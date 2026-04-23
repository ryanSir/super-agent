import os

from anthropic import AsyncAnthropic
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
import  dotenv
dotenv.load_dotenv()

TOKEN = os.environ['OPENAI_API_KEY']

anthropic_client = AsyncAnthropic(
    api_key=TOKEN,
    base_url='http://rd-gateway.patsnap.info',
    default_headers={
        'Authorization': f'Bearer {TOKEN}',
        'x-api-key': TOKEN,
    }
)

model = AnthropicModel(
    'claude-4.6-sonnet',
    provider=AnthropicProvider(anthropic_client=anthropic_client)
)
agent = Agent(
    model,
    instructions='Be concise, reply with one sentence.'

)
result = agent.run_sync('Where does "hello world" come from?')
print(result.output)
"""
The first known use of "hello, world" was in a 1974 textbook about the C programming language.
"""
