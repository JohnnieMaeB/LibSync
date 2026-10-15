---
title: The expert that couldn't check anything
date: 2026-10-20
order: 2
unlisted: true
series: Part 2 of 18
description: My first system prompt claimed expertise in platforms the chatbot had no data for. The audit that found it, and the rule that came out of it.
---
In October 2025, my library chatbot's system prompt said:

> You are a master of the library's e-book, audiobook, and streaming platforms (e.g., Libby/OverDrive, Kanopy, Hoopla).

That line was in my first version, committed by me, before any coding agent had touched the prompt. The chatbot had access to none of those platforms.

## A fluent, cheerful, invented answer

It answered anyway. Ask whether a book was on Libby and you'd get a confident yes or no, delivered with the warmth of someone who'd just checked. Nothing had been checked.

In a demo, a confident answer and a correct one look identical. That's the trap. I'd given the model a persona that claimed knowledge, the model did what models do with a persona, and nothing in the system pushed back, because nothing in the system knew the difference.

## The part I'm still half proud of

The prompt also held something I'd defend today in spirit: the full text of the RUSA reference-interview guidelines, the ALA Library Bill of Rights and the ALA Core Values, pasted in verbatim.

I was a few months into grad school and working a library desk, and encoding the profession's standards into the assistant was a library-science instinct. I think the instinct was right: a library assistant should behave the way the profession says a library worker should, and those documents are where the profession wrote that down.

The implementation was the problem. It was about 2,300 tokens of pasted documents, most of it written for human staff standing at a desk, about how to be approachable and how to conduct a reference interview in person. A language model can't use half of that.

Four days later, Google's Jules agent wrapped the pasted text in tidy XML tags, with names like `primary_instructions`, `guiding_principles` and `knowledge_source`. That made a pile of text look like architecture. Nobody questioned the size. That includes me.

## The audit

In July 2026, when I started building with Claude Code, the first document it wrote wasn't code. It was an audit of what the system actually did, as opposed to what the prompt claimed. Here is the core of it:

| Area | What the prompt implied | What was true |
|---|---|---|
| Persona | Expertise across several platforms | Libby, hoopla and Kanopy have no public API, and OverDrive's are partner-only. No data behind the claim. |
| Retrieval | A policy knowledge base | A Pinecone index of 10 hardcoded policy strings, behind an endpoint that couldn't query them (next post). |
| Memory | A conversation | None. One message in, one reply out. |
| Observability | Production-ready | `print()` statements. |

That is not a flattering list for a project with "AI" in the pitch. I'm including it anyway because the list is what made the next decision obvious.

## The rule

The audit gave me the rule that has driven every decision since: **every answer is grounded in something the system actually retrieved, or it says it doesn't know.**

A library patron is the wrong person to hand a confident guess. The whole purpose of a library is that you can trust where the answer came from. An assistant that sounds authoritative and is sometimes invented would damage the thing it's built to serve.

That one rule shaped later work. It's why catalog lookups are backed by Open Library, a real public source. It's why the assistant says plainly what it can't check, which is the subject of Part 6. And it's why I eventually wrote evals that punish confident inventions.

## What I'd say about my own part in this

Two of the three mistakes in this story are mine: the over-claiming persona and the pasted documents. The third, the XML wrapping, was an agent's contribution. All three predate Claude Code. I'm leading with this because the series is only worth reading if it's honest about where the errors came from, and "the AI got it wrong" is the easy story.

What I got right was caring about the profession's standards. What I got wrong was assuming that writing something into a prompt is the same as the system being able to do it. An agent will faithfully implement whatever you put in a prompt, mistakes included, so supplying the domain knowledge is the architect's job, and so is questioning how it gets encoded.

I don't yet know the best way to carry professional ethics into an AI assistant. A distilled set of principles beats a pasted document (Part 15 returns to this), but I'm not sure a short list captures what a good reference interview actually is. If you teach reference or work a desk, I'd like to know what I'm missing.

> **Architect's note:** an agent faithfully implements whatever you put in the prompt, mistakes included. Supplying the domain knowledge is the architect's job. So is questioning how it gets encoded.

What did your first AI prototype claim to know that it couldn't?

*Part 2 of 18. Next: an endpoint that looked finished and could never have worked.*
