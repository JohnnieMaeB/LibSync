"""The HHEM faithfulness evaluator's plumbing (evals/faithfulness.py). HHEM
itself runs only in the weekly eval workflow; here a stand-in scorer records
what it would be asked."""

from types import SimpleNamespace

from evals.faithfulness import PolicyFaithfulness, clean_for_scoring
from evals.task import EvalOutput

POLICY = "Items may be renewed up to three times online or by phone, as long as no one else has placed a hold on them."


def test_markdown_becomes_plain_sentences():
    reply = "**Renewals:**\n\n- Up to **3 times**\n- Online or by `phone`\n\nSee [the policy](https://x.example)."
    assert clean_for_scoring(reply) == "Renewals: Up to 3 times. Online or by phone. See the policy."


def test_referral_sentences_are_dropped():
    reply = "You can renew up to three times. For anything else, please ask library staff! Contact us any time."
    assert clean_for_scoring(reply) == "You can renew up to three times."


def test_pleasantries_and_emoji_are_dropped():
    reply = "You can renew it up to three times. Happy reading! 📚✨ If you have any other questions, just let me know!"
    assert clean_for_scoring(reply) == "You can renew it up to three times."


def test_a_referral_the_policy_itself_states_is_kept():
    policy = "Request forms are at the circulation desk."
    reply = "Request forms are at the circulation desk."
    assert clean_for_scoring(reply, policy) == reply


def _ctx(reply: str, sources: list[str]):
    return SimpleNamespace(output=EvalOutput(reply=reply, tools_called=[], policy_sources=sources))


def test_scores_policy_answers_against_the_retrieved_text():
    asked = []

    def scorer(pairs):
        asked.extend(pairs)
        return [0.91]

    result = PolicyFaithfulness(scorer).evaluate(_ctx("Up to three times. Ask library staff for help.", [POLICY]))
    assert asked == [(POLICY, "Up to three times.")]
    assert result["hhem"].value == 0.91


def test_no_score_without_policy_text_or_without_hhem():
    assert PolicyFaithfulness(lambda pairs: [1.0]).evaluate(_ctx("A book answer.", [])) == {}
    assert PolicyFaithfulness(None).evaluate(_ctx("Up to three times.", [POLICY])) == {}
