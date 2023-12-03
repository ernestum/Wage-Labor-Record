# Wage Labor Record

Wage Labor Record is a tool to help you to keep track of what you did for whom 
and how much time you spent on it ... if you are into that kind of thing.

## This one weird trick to live a comfortable life

I recently discovered this trick to live a comfortable life:
> You help people with their problems, and they give you some token in return.

Here they call this the "service economy" and the tokens are called "money".
I also found out that it is a lot easier when you:
1. Talk to them before you do something for them and find an agreement on what you will do and what you will get in return. They call it a "contract".
2. Write down what you did, how much time you spent on it and how many tokens you like to get in return. They call this writing an "invoice".

If you give those tokens to other people, they are **vastly more likely to let your use food and shelter** that they own[^1].
Or they might be willing to do something for you in return.

This software tool helps you to record what tasks you did for whom and how much time you spent on it.

[^1]: "Ownership" is a widely accepted social construct here.
If you own something you are to decide who can use it and what to do with it.
If necessary, people are convinced to play by those "ownership" by violence.
Violence means harming somebodies mental and/or physical well-being in a way that they don't want to happen.
However, most of the time people play by those rules since the think that "ownership" is a nice idea, and they don't want to ruin it for everybody.

## Why chose WLR?

There are lots of other time tracking software. 
I did not try all of them, but I made the following observations:
- The simple ones often only run in the CLI. 
  This means I cannot see at a glance if and what task I am recording right now. 
  Those tools also won't be able to detect any idle time and remind me about it.
- The GUI ones are mostly overtly complex and require way too many clicks. 
  The friction to use them day-to-day is way too high.
- The ones with a decent usability **and** GUI are proprietary solutions tied to some
  cloud infrastructure, and at some point they drop support for the Linux desktop client 
  (looking at your Toggle Track ...)

So this time tracker tries to
- provide a minimal GUI that does not get into my way
- never needs an internet connection to work or any cloud infrastructure
- be simple enough that I can afford to maintain it over the next years 
  and adapt it to unforeseen needs in the future

### Features
- Detect idle time, remind me about it, let me decide what to do with it
- Low friction: let me start tracking with a single click and decide later what I actually did
- Human-Readable file format
- UI
  - Explorable (cli is not enough)
  - Linux Desktop integration
  - Indicate if I am currently tracking time via tray icon
  - Centered around tray
- Minimal dependencies (make it future-proof)
- Minimal configuration needed/Sensible defaults

### Non-Features
- Internet connectivity
- Using the electron framework to eat CPU, RAM and battery

## Dependencies
- `xprintidle` as a dependency to detect idle time.
- GTK 3.0 for the GUI

## Development Resources
- [Gtk 3.0 API Documentation](https://lazka.github.io/pgi-docs/Gtk-3.0)
- [PyGObject tutorial](https://pygobject.readthedocs.io/)
- [Python GTK+ 3 tutorial](https://python-gtk-3-tutorial.readthedocs.io)
- [How to install PyGObject](https://pygobject.readthedocs.io/en/latest/getting_started.html#ubuntu-getting-started)

## Alternatives to this and why they don't work for me

- [jupyter-timetracker](https://pypi.org/project/jupyter-timetracker/) - GUI too complex/too close to DB editing tools. No support for clients
- [tim](https://github.com/MatthiasKauer/tim) CLI only, no idle time detection but uses hledger as a backend!
- [salary-timetracker](https://pypi.org/project/salary-timetracker/) CLI only, tracking bound to git repos, fixed hourly rate but hey it uses CSV files!
- [ttrac](https://pypi.org/project/ttrac/) CLI only, no idle time detection, no support for clients or tasks but uses JSON files!
- [tickertock](https://pypi.org/project/tickertock/) only with a StreamDeck, wants to use cloud service as backend but uses a hardware interface!
- [mttt](https://pypi.org/project/mttt/) CLI only, no idle time detection but uses plain text files!
- [tt-cli](https://github.com/a1fred/tt) CLI only, no idle time detection, no support for clients 
- [timetracker](https://pypi.org/project/timetracker/) CLI only, no idle time detection, no support for clients
- [hamster](https://github.com/projecthamster/hamster) comes pretty close but seems outdated/abandoned and a little bit too complex