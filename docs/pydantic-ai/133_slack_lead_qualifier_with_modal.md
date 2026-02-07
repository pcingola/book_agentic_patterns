# Slack Lead Qualifier with Modal

In this example, we're going to build an agentic app that:

- automatically researches each new member that joins a company's public Slack community to see how good of a fit they are for the company's commercial product,
- sends this analysis into a (private) Slack channel, and
- sends a daily summary of the top 5 leads from the previous 24 hours into a (different) Slack channel.

We'll be deploying the app on [Modal](https://modal.com), as it lets you use Python to define an app with web endpoints, scheduled functions, and background functions, and deploy them with a CLI, without needing to set up or manage any infrastructure. It's a great way to lower the barrier for people in your organization to start building and deploying AI agents to make their jobs easier.

We also add [Pydantic Logfire](https://pydantic.dev/logfire) to get observability into the app and agent as they're running in response to webhooks and the schedule

## Screenshots

This is what the analysis sent into Slack will look like:

This is what the corresponding trace in [Logfire](https://pydantic.dev/logfire) will look like:

All of these entries can be clicked on to get more details about what happened at that step, including the full conversation with the LLM and HTTP requests and responses.

## Prerequisites

If you just want to see the code without actually going through the effort of setting up the bits necessary to run it, feel free to [jump ahead](#the-code).

### Slack app

You need to have a Slack workspace and the necessary permissions to create apps.

2. Create a new Slack app using the instructions at <https://docs.slack.dev/quickstart>.

   1. In step 2, "Requesting scopes", request the following scopes:
      - [`users.read`](https://docs.slack.dev/reference/scopes/users.read)
      - [`users.read.email`](https://docs.slack.dev/reference/scopes/users.read.email)
      - [`users.profile.read`](https://docs.slack.dev/reference/scopes/users.profile.read)
   1. In step 3, "Installing and authorizing the app", note down the Access Token as we're going to need to store it as a Secret in Modal.
   1. You can skip steps 4 and 5. We're going to need to subscribe to the `team_join` event, but at this point you don't have a webhook URL yet.

1. Create the channels the app will post into, and add the Slack app to them:

   - `#new-slack-leads`
   - `#daily-slack-leads-summary`

   These names are hard-coded in the example. If you want to use different channels, you can clone the repo and change them in `examples/pydantic_examples/slack_lead_qualifier/functions.py`.

### Logfire Write Token

1. If you don't have a Logfire account yet, create one on <https://logfire-us.pydantic.dev/>.
1. Create a new project named, for example, `slack-lead-qualifier`.
1. Generate a new Write Token and note it down, as we're going to need to store it as a Secret in Modal.

### OpenAI API Key

1. If you don't have an OpenAI account yet, create one on <https://platform.openai.com/>.
1. Create a new API Key in Settings and note it down, as we're going to need to store it as a Secret in Modal.

### Modal account

1. If you don't have a Modal account yet, create one on <https://modal.com/signup>.
1. Create 3 Secrets of type "Custom" on <https://modal.com/secrets>:
   - Name: `slack`, key: `SLACK_API_KEY`, value: the Slack Access Token you generated earlier
   - Name: `logfire`, key: `LOGFIRE_TOKEN`, value: the Logfire Write Token you generated earlier
   - Name: `openai`, key: `OPENAI_API_KEY`, value: the OpenAI API Key you generated earlier

## Usage

1. Make sure you have the [dependencies installed](https://ai.pydantic.dev/examples/setup/#usage).

1. Authenticate with Modal:

   ```bash
   python/uv-run -m modal setup
   ```

1. Run the example as an [ephemeral Modal app](https://modal.com/docs/guide/apps#ephemeral-apps), meaning it will only run until you quit it using Ctrl+C:

   ```bash
   python/uv-run -m modal serve -m pydantic_ai_examples.slack_lead_qualifier.modal
   ```

1. Note down the URL after `Created web function web_app =>`, this is your webhook endpoint URL.

1. Go back to <https://docs.slack.dev/quickstart> and follow step 4, "Configuring the app for event listening", to subscribe to the `team_join` event with the webhook endpoint URL you noted down as the Request URL.

Now when someone new (possibly you with a throwaway email) joins the Slack workspace, you'll see the webhook event being processed in the terminal where you ran `modal serve` and in the Logfire Live view, and after waiting a few seconds you should see the result appear in the `#new-slack-leads` Slack channel!

Faking a Slack signup

You can also fake a Slack signup event and try out the agent like this, with any name or email you please:

```bash
curl -X POST <webhook endpoint URL> \
-H "Content-Type: application/json" \
-d '{
    "type": "event_callback",
    "event": {
        "type": "team_join",
        "user": {
            "profile": {
                "email": "samuel@pydantic.dev",
                "first_name": "Samuel",
                "last_name": "Colvin",
                "display_name": "Samuel Colvin"
            }
        }
    }
}'
```

Deploying to production

If you'd like to deploy this app into your Modal workspace in a persistent fashion, you can use this command:

```bash
python/uv-run -m modal deploy -m pydantic_ai_examples.slack_lead_qualifier.modal
```

You'll likely want to [download the code](https://github.com/pydantic/pydantic-ai/tree/main/examples/pydantic_ai_examples/slack_lead_qualifier) first, put it in a new repo, and then do [continuous deployment](https://modal.com/docs/guide/continuous-deployment#github-actions) using GitHub Actions.

Don't forget to update the Slack event request URL to the new persistent URL! You'll also want to modify the [instructions for the agent](#agent) to your own situation.

## The code

We're going to start with the basics, and then gradually build up into the full app.

### Models

#### `Profile`

First, we define a [Pydantic](https://docs.pydantic.dev) model that represents a Slack user profile. These are the fields we get from the [`team_join`](https://docs.slack.dev/reference/events/team_join) event that's sent to the webhook endpoint that we'll define in a bit.

[slack_lead_qualifier/models.py (L11-L15)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/models.py#L11-L15)

```python
...

class Profile(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    email: str

...
```

We also define a `Profile.as_prompt()` helper method that uses format_as_xml to turn the profile into a string that can be sent to the model.

[slack_lead_qualifier/models.py (L7-L19)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/models.py#L7-L19)

```python
...

from pydantic_ai import format_as_xml

...

class Profile(BaseModel):

...

    def as_prompt(self) -> str:
        return format_as_xml(self, root_tag='profile')

...
```

#### `Analysis`

The second model we'll need represents the result of the analysis that the agent will perform. We include docstrings to provide additional context to the model on what these fields should contain.

[slack_lead_qualifier/models.py (L23-L31)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/models.py#L23-L31)

```python
...

class Analysis(BaseModel):
    profile: Profile
    organization_name: str
    organization_domain: str
    job_title: str
    relevance: Annotated[int, Ge(1), Le(5)]
    """Estimated fit for Pydantic Logfire: 1 = low, 5 = high"""
    summary: str
    """One-sentence welcome note summarising who they are and how we might help"""

...
```

We also define a `Analysis.as_slack_blocks()` helper method that turns the analysis into some [Slack blocks](https://api.slack.com/reference/block-kit/blocks) that can be sent to the Slack API to post a new message.

[slack_lead_qualifier/models.py (L23-L46)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/models.py#L23-L46)

```python
...

class Analysis(BaseModel):

...

    def as_slack_blocks(self, include_relevance: bool = False) -> list[dict[str, Any]]:
        profile = self.profile
        relevance = f'({self.relevance}/5)' if include_relevance else ''
        return [
            {
                'type': 'markdown',
                'text': f'[{profile.display_name}](mailto:{profile.email}), {self.job_title} at [**{self.organization_name}**](https://{self.organization_domain}) {relevance}',
            },
            {
                'type': 'markdown',
                'text': self.summary,
            },
        ]
```

### Agent

Now it's time to get into Pydantic AI and define the agent that will do the actual analysis!

We specify the model we'll use (`openai:gpt-5`), provide [instructions](https://ai.pydantic.dev/agent/#instructions), give the agent access to the [DuckDuckGo search tool](https://ai.pydantic.dev/common-tools/#duckduckgo-search-tool), and tell it to output either an `Analysis` or `None` using the [Native Output](https://ai.pydantic.dev/output/#native-output) structured output mode.

The real meat of the app is in the instructions that tell the agent how to evaluate each new Slack member. If you plan to use this app yourself, you'll of course want to modify them to your own situation.

[Learn about Gateway](https://ai.pydantic.dev/gateway) [slack_lead_qualifier/agent.py (L7-L40)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/agent.py#L7-L40)

```python
...

from pydantic_ai import Agent, NativeOutput
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

...

agent = Agent(
    'gateway/openai:gpt-5.2',
    instructions=dedent(
        """
        When a new person joins our public Slack, please put together a brief snapshot so we can be most useful to them.

        **What to include**

        1. **Who they are:**  Any details about their professional role or projects (e.g. LinkedIn, GitHub, company bio).
        2. **Where they work:**  Name of the organisation and its domain.
        3. **How we can help:**  On a scale of 1â€“5, estimate how likely they are to benefit from **Pydantic Logfire**
           (our paid observability tool) based on factors such as company size, product maturity, or AI usage.
           *1 = probably not relevant, 5 = very strong fit.*

        **Our products (for context only)**
        â€¢ **Pydantic Validation** â€“ Python data-validation (open source)
        â€¢ **Pydantic AI** â€“ Python agent framework (open source)
        â€¢ **Pydantic Logfire** â€“ Observability for traces, logs & metrics with first-class AI support (commercial)

        **How to research**

        â€¢ Use the provided DuckDuckGo search tool to research the person and the organization they work for, based on the email domain or what you find on e.g. LinkedIn and GitHub.
        â€¢ If you can't find enough to form a reasonable view, return **None**.
        """
    ),
    tools=[duckduckgo_search_tool()],
    output_type=NativeOutput([Analysis, NoneType]),
)

...
```

[slack_lead_qualifier/agent.py (L7-L40)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/agent.py#L7-L40)

```python
...

from pydantic_ai import Agent, NativeOutput
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

...

agent = Agent(
    'openai:gpt-5.2',
    instructions=dedent(
        """
        When a new person joins our public Slack, please put together a brief snapshot so we can be most useful to them.

        **What to include**

        1. **Who they are:**  Any details about their professional role or projects (e.g. LinkedIn, GitHub, company bio).
        2. **Where they work:**  Name of the organisation and its domain.
        3. **How we can help:**  On a scale of 1â€“5, estimate how likely they are to benefit from **Pydantic Logfire**
           (our paid observability tool) based on factors such as company size, product maturity, or AI usage.
           *1 = probably not relevant, 5 = very strong fit.*

        **Our products (for context only)**
        â€¢ **Pydantic Validation** â€“ Python data-validation (open source)
        â€¢ **Pydantic AI** â€“ Python agent framework (open source)
        â€¢ **Pydantic Logfire** â€“ Observability for traces, logs & metrics with first-class AI support (commercial)

        **How to research**

        â€¢ Use the provided DuckDuckGo search tool to research the person and the organization they work for, based on the email domain or what you find on e.g. LinkedIn and GitHub.
        â€¢ If you can't find enough to form a reasonable view, return **None**.
        """
    ),
    tools=[duckduckgo_search_tool()],
    output_type=NativeOutput([Analysis, NoneType]),
)

...
```

#### `analyze_profile`

We also define a `analyze_profile` helper function that takes a `Profile`, runs the agent, and returns an `Analysis` (or `None`), and instrument it using [Logfire](https://ai.pydantic.dev/logfire/index.md).

[slack_lead_qualifier/agent.py (L44-L47)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/agent.py#L44-L47)

```python
...

@logfire.instrument('Analyze profile')
async def analyze_profile(profile: Profile) -> Analysis | None:
    result = await agent.run(profile.as_prompt())
    return result.output
```

### Analysis store

The next building block we'll need is a place to store all the analyses that have been done so that we can look them up when we send the daily summary.

Fortunately, Modal provides us with a convenient way to store some data that can be read back in a subsequent Modal run (webhook or scheduled): [`modal.Dict`](https://modal.com/docs/reference/modal.Dict).

We define some convenience methods to easily add, list, and clear analyses.

[slack_lead_qualifier/store.py (L4-L31)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/store.py#L4-L31)

```python
...

import modal

...

class AnalysisStore:
    @classmethod
    @logfire.instrument('Add analysis to store')
    async def add(cls, analysis: Analysis):
        await cls._get_store().put.aio(analysis.profile.email, analysis.model_dump())

    @classmethod
    @logfire.instrument('List analyses from store')
    async def list(cls) -> list[Analysis]:
        return [
            Analysis.model_validate(analysis)
            async for analysis in cls._get_store().values.aio()
        ]

    @classmethod
    @logfire.instrument('Clear analyses from store')
    async def clear(cls):
        await cls._get_store().clear.aio()

    @classmethod
    def _get_store(cls) -> modal.Dict:
        return modal.Dict.from_name('analyses', create_if_missing=True)  # type: ignore
```

Note

Note that `# type: ignore` on the last line -- unfortunately `modal` does not fully define its types, so we need this to stop our static type checker `pyright`, which we run over all Pydantic AI code including examples, from complaining.

### Send Slack message

Next, we'll need a way to actually send a Slack message, so we define a simple function that uses Slack's [`chat.postMessage`](https://api.slack.com/methods/chat.postMessage) API.

[slack_lead_qualifier/slack.py (L8-L30)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/slack.py#L8-L30)

```python
...

API_KEY = os.getenv('SLACK_API_KEY')
assert API_KEY, 'SLACK_API_KEY is not set'


@logfire.instrument('Send Slack message')
async def send_slack_message(channel: str, blocks: list[dict[str, Any]]):
    client = httpx.AsyncClient()
    response = await client.post(
        'https://slack.com/api/chat.postMessage',
        json={
            'channel': channel,
            'blocks': blocks,
        },
        headers={
            'Authorization': f'Bearer {API_KEY}',
        },
        timeout=5,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get('ok', False):
        error = result.get('error', 'Unknown error')
        raise Exception(f'Failed to send to Slack: {error}')
```

### Features

Now we can start putting these building blocks together to implement the actual features we want!

#### `process_slack_member`

This function takes a [`Profile`](#profile), [analyzes](#analyze_profile) it using the agent, adds it to the [`AnalysisStore`](#analysis-store), and [sends](#send-slack-message) the analysis into the `#new-slack-leads` channel.

[slack_lead_qualifier/functions.py (L4-L45)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/functions.py#L4-L45)

```python
...

from .agent import analyze_profile
from .models import Profile

from .slack import send_slack_message
from .store import AnalysisStore

...

NEW_LEAD_CHANNEL = '#new-slack-leads'

...

@logfire.instrument('Process Slack member')
async def process_slack_member(profile: Profile):
    analysis = await analyze_profile(profile)
    logfire.info('Analysis', analysis=analysis)

    if analysis is None:
        return

    await AnalysisStore().add(analysis)

    await send_slack_message(
        NEW_LEAD_CHANNEL,
        [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f'New Slack member with score {analysis.relevance}/5',
                },
            },
            {
                'type': 'divider',
            },
            *analysis.as_slack_blocks(),
        ],
    )

...
```

#### `send_daily_summary`

This function list all of the analyses in the [`AnalysisStore`](#analysis-store), takes the top 5 by relevance, [sends](#send-slack-message) them into the `#daily-slack-leads-summary` channel, and clears the `AnalysisStore` so that the next daily run won't process these analyses again.

[slack_lead_qualifier/functions.py (L8-L85)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/functions.py#L8-L85)

```python
...

from .slack import send_slack_message
from .store import AnalysisStore

...

DAILY_SUMMARY_CHANNEL = '#daily-slack-leads-summary'

...

@logfire.instrument('Send daily summary')
async def send_daily_summary():
    analyses = await AnalysisStore().list()
    logfire.info('Analyses', analyses=analyses)

    if len(analyses) == 0:
        return

    sorted_analyses = sorted(analyses, key=lambda x: x.relevance, reverse=True)
    top_analyses = sorted_analyses[:5]

    blocks = [
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': f'Top {len(top_analyses)} new Slack members from the last 24 hours',
            },
        },
    ]

    for analysis in top_analyses:
        blocks.extend(
            [
                {
                    'type': 'divider',
                },
                *analysis.as_slack_blocks(include_relevance=True),
            ]
        )

    await send_slack_message(
        DAILY_SUMMARY_CHANNEL,
        blocks,
    )

    await AnalysisStore().clear()
```

### Web app

As it stands, neither of these functions are actually being called from anywhere.

Let's implement a [FastAPI](https://fastapi.tiangolo.com/) endpoint to handle the `team_join` Slack webhook (also known as the [Slack Events API](https://docs.slack.dev/apis/events-api)) and call the [`process_slack_member`](#process_slack_member) function we just defined. We also instrument FastAPI using Logfire for good measure.

[slack_lead_qualifier/app.py (L20-L36)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/app.py#L20-L36)

```python
...

app = FastAPI()
logfire.instrument_fastapi(app, capture_headers=True)


@app.post('/')
async def process_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    if payload['type'] == 'url_verification':
        return {'challenge': payload['challenge']}
    elif (
        payload['type'] == 'event_callback' and payload['event']['type'] == 'team_join'
    ):
        profile = Profile.model_validate(payload['event']['user']['profile'])

        process_slack_member(profile)
        return {'status': 'OK'}

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
```

#### `process_slack_member` with Modal

I was a little sneaky there -- we're not actually calling the [`process_slack_member`](#process_slack_member) function we defined in `functions.py` directly, as Slack requires webhooks to respond within 3 seconds, and we need a bit more time than that to talk to the LLM, do some web searches, and send the Slack message.

Instead, we're calling the following function defined alongside the app, which uses Modal's [`modal.Function.spawn`](https://modal.com/docs/reference/modal.Function#spawn) feature to run a function in the background. (If you're curious what the Modal side of this function looks like, you can [jump ahead](#backgrounded-process_slack_member).)

Because `modal.py` (which we'll see in the next section) imports `app.py`, we import from `modal.py` inside the function definition because doing so at the top level would have resulted in a circular import error.

We also pass along the current Logfire context to get [Distributed Tracing](https://logfire.pydantic.dev/docs/how-to-guides/distributed-tracing/), meaning that the background function execution will show up nested under the webhook request trace, so that we have everything related to that request in one place.

[slack_lead_qualifier/app.py (L11-L16)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/app.py#L11-L16)

```python
...

def process_slack_member(profile: Profile):
    from .modal import process_slack_member as _process_slack_member

    _process_slack_member.spawn(
        profile.model_dump(), logfire_ctx=get_context()
    )

...
```

### Modal app

Now let's see how easy Modal makes it to deploy all of this.

#### Set up Modal

The first thing we do is define the Modal app, by specifying the base image to use (Debian with Python 3.13), all the Python packages it needs, and all of the secrets defined in the Modal interface that need to be made available during runtime.

[slack_lead_qualifier/modal.py (L4-L21)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/modal.py#L4-L21)

```python
...

import modal

image = modal.Image.debian_slim(python_version='3.13').pip_install(
    'pydantic',
    'pydantic_ai_slim[openai,duckduckgo]',
    'logfire[httpx,fastapi]',
    'fastapi[standard]',
    'httpx',
)
app = modal.App(
    name='slack-lead-qualifier',
    image=image,
    secrets=[
        modal.Secret.from_name('logfire'),
        modal.Secret.from_name('openai'),
        modal.Secret.from_name('slack'),
    ],
)

...
```

#### Set up Logfire

Next, we define a function to set up Logfire instrumentation for Pydantic AI and HTTPX.

We cannot do this at the top level of the file, as the requested packages (like `logfire`) will only be available within functions running on Modal (like the ones we'll define next). This file, `modal.py`, runs on your local machine and only has access to the `modal` package.

[slack_lead_qualifier/modal.py (L25-L30)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/modal.py#L25-L30)

```python
...

def setup_logfire():
    import logfire

    logfire.configure(service_name=app.name)
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=True)

...
```

#### Web app

To deploy a [web endpoint](https://modal.com/docs/guide/webhooks) on Modal, we simply define a function that returns an ASGI app (like FastAPI) and decorate it with `@app.function()` and `@modal.asgi_app()`.

This `web_app` function will be run on Modal, so inside the function we can call the `setup_logfire` function that requires the `logfire` package, and import `app.py` which uses the other requested packages.

By default, Modal spins up a container to handle a function call (like a web request) on-demand, meaning there's a little bit of startup time to each request. However, Slack requires webhooks to respond within 3 seconds, so we specify `min_containers=1` to keep the web endpoint running and ready to answer requests at all times. This is a bit annoying and wasteful, but fortunately [Modal's pricing](https://modal.com/pricing) is pretty reasonable, you get $30 free monthly compute, and they offer up to $50k in free credits for startup and academic researchers.

[slack_lead_qualifier/modal.py (L34-L41)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/modal.py#L34-L41)

```python
...

@app.function(min_containers=1)
@modal.asgi_app()  # type: ignore
def web_app():
    setup_logfire()

    from .app import app as _app

    return _app

...
```

Note

Note that `# type: ignore` on the `@modal.asgi_app()` line -- unfortunately `modal` does not fully define its types, so we need this to stop our static type checker `pyright`, which we run over all Pydantic AI code including examples, from complaining.

#### Scheduled `send_daily_summary`

To define a [scheduled function](https://modal.com/docs/guide/cron), we can use the `@app.function()` decorator with a `schedule` argument. This Modal function will call our imported [`send_daily_summary`](#send_daily_summary) function every day at 8 am UTC.

[slack_lead_qualifier/modal.py (L60-L66)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/modal.py#L60-L66)

```python
...

@app.function(schedule=modal.Cron('0 8 * * *'))  # Every day at 8am UTC
async def send_daily_summary():
    setup_logfire()

    from .functions import send_daily_summary as _send_daily_summary

    await _send_daily_summary()
```

#### Backgrounded `process_slack_member`

Finally, we define a Modal function that wraps our [`process_slack_member`](#process_slack_member) function, so that it can run in the background.

As you'll remember from when we [spawned this function from the web app](#process_slack_member-with-modal), we passed along the Logfire context to get [Distributed Tracing](https://logfire.pydantic.dev/docs/how-to-guides/distributed-tracing/), so we need to attach it here.

[slack_lead_qualifier/modal.py (L45-L56)](https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/slack_lead_qualifier/modal.py#L45-L56)

```python
...

@app.function()
async def process_slack_member(profile_raw: dict[str, Any], logfire_ctx: Any):
    setup_logfire()

    from logfire.propagate import attach_context

    from .functions import process_slack_member as _process_slack_member
    from .models import Profile

    with attach_context(logfire_ctx):
        profile = Profile.model_validate(profile_raw)
        await _process_slack_member(profile)

...
```

## Conclusion

And that's it! Now, assuming you've met the [prerequisites](#prerequisites), you can run or deploy the app using the commands under [usage](#usage).
