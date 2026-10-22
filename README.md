# GA-Optimised Fuzzy Traffic-Signal Control

Soft Computing AAT (23CS7PESCN / 23CS8PESCN), B.M.S. College of Engineering, Problem Statement 12:
optimise a fuzzy traffic-signal controller for a congested three-junction corridor to reduce average
vehicle delay compared with fixed-time plans.

**Live demo:** https://lakshay1518.github.io/fuzzy-traffic-signals/

- `index.html`: interactive demo (corridor replay, fuzzy controller, results). Works offline too.
- `report.pdf`: project report.
- `source-code.zip`: Python source, unit tests and results. The fuzzy inference system, genetic
  algorithm and traffic simulator use only the Python standard library.

Result: on 10 unseen random seeds, the final GA-tuned fuzzy controller reduced average delay
compared with a Webster fixed-time plan in all six demand scenarios, by 3.8 % to 26.3 %.
