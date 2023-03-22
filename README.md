# Wage Labor Record

Wage Labor Record is a simple time tracking tool that helps you to keep track of what 
you did for whom and how much time you spent on it ... if you are into that kind of thing.

## This one weird trick to live a comfortable life

I recently discovered this trick to live a comfortable life:
> You help people with their problems, and they give you some token in return.

Here they call this the "service economy" and the tokens are called "money".
I also found out that it is a lot easier when you:
1. Talk to them before you do something for them and find an agreement on what you will do and what you will get in return. They call it "contract".
2. Write down what you did, how much time you spent on it and how many tokens you like to get in return. They call this writing an "invoice".

If you give those tokens to other people, they are **vastly more likely to let your use food and shelter** that they own[^1].

This software tool helps you to record what tasks you did for whom and how much time you spent on it.

[^1]: "Ownership" is a widely accepted social construct here.
If you own something you are to decide who can use it and what to do with it.
If necessary, people are convinced to play by those "ownership" by violence.
Violence means harming somebodies mental and/or physical well-being in a way that they don't want to happen.
However, most of the time people play by those rules since the think that "ownership" is a nice idea, and they don't want to ruin it for everybody.

## What this is not

This system with the money is reliable but there a lots of other, much nicer, ways to interact with people that do not involve keeping track of numbers.
I recommend trying out as many as possible. 
Be warned though, mixing them is often quite difficult.
Therefore, I **do not recommend the usage of this tools outside the scope of its original purpose**.
E.g. many people keep track of what they did to prove something to themselves or to people they live with.
However, this is just a bad proxy for true self-introspection or an honest discussion between flatmates!

## Why chose WLR?

There is lots of other time tracking software. I did not try all of them, but I made the following observations:
- The simple ones often only run in the CLI. This means I can not see at a glance if and what task I am recording right now. Those tools also won't be able to detect any idle time and remind me about it.
- The GUI ones are mostly overtly complex and require way too many clicks. The friction to use them day-to-day is way too high.
- The ones with a decent usability **and** GUI are proprietary solutions tied to some funny cloud thingy and at some point they drop support for the Linux desktop client (looking at you Toggle Track ...)
- None of them are reliably able to position themselves in relation to the social contract or distance themselves from the quantified self movement. 

So this time tracker tries to
- provide a minimal GUI that does not get into my way
- never needs an internet connection to work or any cloud infrastructure
- is simple enough that I can afford to maintain it over the next years and adapt it to unforseen needs in the future



## Requirements
- Detect idle time, remind me about it, let me decide what to do with it
- Low friction: let me start tracking right away and decide later what I actually did
- Human-Readable file format
- CLI
  - Explorable (cli is not enough)
  - Linux Desktop integration
  - Let me see if I am currently tracking time via tray icon
  - Centered around tray
- Minimal dependencies (make it future-proof)
- Minimal configuration needed/Sensible defaults

## Non-Requirements
- Cloud connectivity
- Electron App
- Monitoring your employees time

## Dependencies
needs `xprintidle` as a dependency

## Development Resources
- [Gtk 3.0 API Documentation](https://lazka.github.io/pgi-docs/Gtk-3.0)
- [PyGObject tutorial](https://pygobject.readthedocs.io/)
- [How to install PyGObject](https://pygobject.readthedocs.io/en/latest/getting_started.html#ubuntu-getting-started)

## Alternatives to this and why they don't work for me

- [jupyter-timetracker](https://pypi.org/project/jupyter-timetracker/) - GUI too complex/too close to DB editing tools. No support for clients
- [tim](https://github.com/MatthiasKauer/tim) Command line only. Won't remind me of idle time
- [salary-timetracker](https://pypi.org/project/salary-timetracker/) CLI only
- [ttrac](https://pypi.org/project/ttrac/) CLI only
- [tickertock](https://pypi.org/project/tickertock/) only with a StreamDeck. Cool idea though!
- [mttt](https://pypi.org/project/mttt/) CLI only
- [tt-cli](https://github.com/a1fred/tt) CLI only
- [timetracker](https://pypi.org/project/timetracker/) CLI only
- hamster outdated