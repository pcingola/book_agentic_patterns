# Hands-On: Basic Evals

Evals transform informal confidence ("this agent seems to work") into repeatable, versioned evidence about correctness. This hands-on explores three fundamental evaluation approaches through `example_evals.ipynb`, progressing from simple string matching to LLM-as-a-Judge.

## Why Evals Matter

Testing agentic systems differs fundamentally from testing deterministic software. An agent's output varies across runs, depends on model behavior, and often lacks a single "correct" answer. Evals address this by defining what "good" means for a given task and measuring whether outputs meet that definition.

The simplest evals check for specific content in responses. More sophisticated approaches use structured outputs to make assertions trivial, or employ another LLM to judge quality against a rubric. Each approach trades off simplicity against flexibility.

## String Matching Eval

The most basic eval checks whether a response contains expected content:

```python
async def test_simple_eval():
    agent = get_agent()
    prompt = "What's the capital of Nepal?"
    agent_run, _ = await run_agent(agent, prompt)
    answer = agent_run.result.output
    print(f"Agent's answer: {answer}")
    assert 'kathmandu' in answer.lower()
```

This pattern works for factual questions with known answers. The agent might respond with "The capital of Nepal is Kathmandu" or "Kathmandu is Nepal's capital city" - both pass because they contain the expected substring.

The `.lower()` call handles case variation, a common source of false failures. Without it, "Kathmandu" and "kathmandu" would be treated as different strings.

String matching has clear limitations. It cannot handle paraphrasing, synonyms, or equivalent but differently-worded answers. For the capital of Nepal, this works because there's exactly one correct answer with one spelling. For more complex questions, string matching becomes brittle.

## Structured Output Eval

Structured outputs eliminate parsing ambiguity by constraining the model to return typed values:

```python
async def test_simple_eval_structured():
    agent = get_agent(output_type=bool)
    prompt = "Is the capital of Nepal Kathmandu?"
    agent_run, _ = await run_agent(agent, prompt)
    answer = agent_run.result.output
    print(f"Agent's answer: {answer}")
    assert answer is True
```

The `output_type=bool` parameter tells the agent to return a boolean rather than free-form text. The model still reasons about the question, but its final output is constrained to `True` or `False`.

This approach transforms eval assertions from string parsing into type checking. Instead of searching for substrings in variable text, we compare typed values directly. The assertion `answer is True` is unambiguous and deterministic.

Structured outputs work well when you can frame the evaluation as a typed question. Binary yes/no questions naturally map to booleans. Multiple choice questions map to enums. Numeric questions map to integers or floats. The key insight is that constraining the output format often makes evaluation trivial.

The tradeoff is that not all tasks fit neatly into structured formats. Open-ended generation, creative writing, and explanatory tasks resist simple typing. For these, we need evaluation approaches that can handle free-form text.

## LLM-as-a-Judge

When outputs are open-ended and lack exact correct answers, another LLM can evaluate quality:

```python
async def judge(question: str, answer: str) -> None:
    """Judge if the answer is correct for the given question."""
    judge_agent = get_agent(output_type=bool)
    judge_prompt = f"""
# Judge

Given a question, judge if the following answer is correct.

## Question

{question}

## Answer

{answer}
"""
    agent_run, _ = await run_agent(judge_agent, judge_prompt)
    is_correct = agent_run.result.output
    print(f"Judge verdict: {is_correct}")
    assert is_correct is True
```

The judge receives both the original question and the agent's answer, then determines whether the answer correctly addresses the question. Using `output_type=bool` ensures the judge returns a clear verdict rather than hedging in prose.

The test function generates an answer and passes it to the judge:

```python
async def test_llm_as_a_judge():
    agent = get_agent()
    question = "Why is the sky blue?"
    agent_run, _ = await run_agent(agent, question)
    answer = agent_run.result.output
    print(f"Agent's answer: {answer}")
    await judge(question, answer)
```

This two-step process separates generation from evaluation. The first agent answers the question freely. The second agent (the judge) evaluates whether that answer is correct. The judge can assess semantic correctness, factual accuracy, and completeness in ways that string matching cannot.

LLM-as-a-Judge scales to tasks where defining correctness programmatically is impractical. A judge can evaluate whether an explanation is clear, whether a summary captures key points, or whether code follows best practices. The rubric (the judge prompt) encodes what "good" means for the specific task.

## Choosing an Approach

The three approaches form a hierarchy of complexity and flexibility:

String matching is fastest and most deterministic but only works for exact factual queries with predictable answer formats. Use it when you know exactly what substring should appear in a correct response.

Structured outputs add flexibility by letting the model reason freely while constraining the output format. Use them when the evaluation can be framed as a typed question (yes/no, multiple choice, numeric).

LLM-as-a-Judge handles open-ended tasks where correctness is semantic rather than syntactic. Use it when you need to evaluate quality, accuracy, or adherence to guidelines that resist simple rules.

In practice, production eval suites combine all three. Deterministic checks run first as fast filters. Structured output checks handle typed validations. Judge-based evaluation handles nuanced quality assessment. This layering optimizes for both speed and coverage.

## Limitations and Considerations

Each approach has limitations worth understanding.

String matching fails on paraphrasing and equivalent formulations. An answer might be correct but use different words than expected.

Structured outputs force the model into constrained formats that may not fit the task. Forcing a boolean on a nuanced question loses information.

LLM judges are non-deterministic, inherit model biases, and add latency and cost. A judge might be wrong, inconsistent across runs, or biased toward certain answer styles (like preferring longer responses).

These limitations don't invalidate the approaches - they inform when to use each one and how to interpret results. Evals are evidence, not proof. Multiple eval approaches on the same task provide stronger evidence than any single approach alone.

## Key Takeaways

Evals convert informal confidence into measurable evidence. String matching works for factual queries with known answers. Structured outputs make assertions trivial by constraining response format. LLM-as-a-Judge handles open-ended tasks through semantic evaluation.

The choice of eval approach depends on the task. Factual lookups use string matching. Typed questions use structured outputs. Open-ended generation uses judges. Production systems typically layer all three for comprehensive coverage.

Evals should be treated as engineering artifacts: versioned, reviewed, and maintained alongside the code they test. The next hands-on explores how the Pydantic Evals framework provides structured abstractions for building eval suites at scale.
