#!/usr/bin/env python3
"""
Patent Legal Status Query Script

Usage:
  python legal_status.py "CN110245964A"
  python legal_status.py "640cd059-3615-4bc6-bec2-f7bd57209733"
  python legal_status.py "CN110245964A" "US10123456B2" "EP3456789A1"
"""

import sys
import json
import os
import re
import argparse
import requests
from typing import Dict, List, Optional, Any


class PatentClient:
    """Patent API Client"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv(
            'PATSNAP_API_BASE',
            'http://qa-s-analytics-hiro.patsnap.info'
        )
        self.base_file_path = os.getenv('AGENT_WORK_DIR', "/home/app/dev-cwd") + "/public"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'PATSNAP_KEY': os.getenv('PATSNAP_KEY', ''),
        })
        self.timeout = 30

    def _is_uuid(self, identifier: str) -> bool:
        identifier = identifier.strip()
        return '-' in identifier and len(identifier) == 36

    def _ensure_patent_id(self, patent_identifier: str) -> Optional[str]:
        patent_identifier = patent_identifier.strip()
        if self._is_uuid(patent_identifier):
            return patent_identifier
        try:
            result = self.query_patent_fields(fields=['TITLE'], pns=[patent_identifier])
            if not result.get('status') or not result.get('data'):
                return None
            data = result['data']
            if isinstance(data, dict):
                return data['patent_id']
            elif isinstance(data, list) and len(data) > 0:
                return data[0]['patent_id']
            return None
        except Exception as e:
            print(f'[DEBUG] Patent number conversion failed ({patent_identifier}): {e}', file=sys.stderr)
            return None

    def query_patent_fields(self, fields: List[str], pns: Optional[List[str]] = None,
                            patent_ids: Optional[List[str]] = None, lang: str = 'cn') -> Dict[str, Any]:
        data = {'fields': fields, 'lang': lang}
        if pns:
            data['pns'] = pns
        if patent_ids:
            data['patent_ids'] = patent_ids
        response = self.session.post(
            f'{self.base_url}/api/patent/fields/query', json=data, timeout=self.timeout
        )
        response.raise_for_status()
        result = response.json()
        if result.get('data'):
            render_type = result.get('render_type', 'patent-list')
            if render_type == 'patent-view':
                if result['data'].get('fields'):
                    self._clean_html_tags(result['data']['fields'])
            elif isinstance(result['data'], list):
                for patent in result['data']:
                    if patent.get('fields'):
                        self._clean_html_tags(patent['fields'])
        return result

    def _clean_html_tags(self, fields: Dict[str, Any]) -> None:
        for key, value in fields.items():
            if isinstance(value, list):
                fields[key] = [self._remove_html_tags(item) if isinstance(item, str) else item for item in value]
            elif isinstance(value, str):
                fields[key] = self._remove_html_tags(value)

    def _remove_html_tags(self, text: str) -> str:
        clean_text = re.sub(r'<[^>]+>', '', text)
        return re.sub(r'\s+', ' ', clean_text).strip()

    def get_legal_status(self, patent_identifier: str, lang: str = 'cn') -> Dict[str, Any]:
        patent_id = self._ensure_patent_id(patent_identifier)
        if not patent_id:
            return {'status': False, 'error': f'Cannot find patent: {patent_identifier}'}
        response = self.session.get(
            f'{self.base_url}/api/patent/legal-status',
            params={'patent_id': patent_id, 'lang': lang},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


def create_patent_client(base_url: Optional[str] = None) -> PatentClient:
    return PatentClient(base_url)


def main():
    parser = argparse.ArgumentParser(
        description='Patent Legal Status Query',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Description:
   - Accepts patent ID (internal UUID) or publication number
   - Supports batch query for multiple patents
   - Returns detailed legal status information

 Use Cases:
   - Infringement risk analysis: confirm whether a patent is active
   - FTO investigation: filter active patents
   - Patent valuation: understand patent rights status
   - Patent due diligence: verify legal status

 Examples:
   $ python legal_status.py "CN110245964A"
   $ python legal_status.py "640cd059-3615-4bc6-bec2-f7bd57209733"
   $ python legal_status.py "CN110245964A" "US10123456B2" "EP3456789A1"
 """
    )

    parser.add_argument(
        'patent_identifier',
        help='Patent ID or publication number'
    )
    parser.add_argument(
        '--base-url',
        help='API base URL'
    )

    args = parser.parse_args()

    client = create_patent_client(args.base_url)

    result = client.get_legal_status(args.patent_identifier)

    # Output result
    output_text = json.dumps(result, ensure_ascii=False)
    print(output_text)


if __name__ == '__main__':
    main()
