"""
Verification part of matching.

We represent clusters as json lines. One example input line (prettified):

    {
      "v": [
        "cjcpmod6pjaczbhrqfljdfl4m4",
        "di5kdt5apfc6fiiqofjzkuiqey",
        "fxhwvmc7dzc6bpuvo7ds4l5gx4",
        "pda5cuevyrcmpgj3woxw7ktvz4",
        "port5bx5nzb7tghqsjknnhs56y",
        "x3a43yczavdkfhp3ekgt5hn6l4"
      ],
      "k": "1 Grundlagen",
      "c": "t"
    }

Further steps:

* fetch all releases, this might be via API, search index, some local key value
store, or some other cache
* apply various rules, return match status
* alternatively: have a few more fields in the intermediate representation (to
keep operation local)

"""
