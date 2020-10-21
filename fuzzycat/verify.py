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

"""

def fetch_release_entity(ident, api="https://api.fatcat.wiki/v0"):
    """
    Fetches a single release entity.
    """
    link = "https://api.fatcat.wiki/v0/release/{}".format(ident)
    return requests.get(link).json()

def ident_to_release_entities(ids):
    """
    Turn a list of ids into release entities.
    """
    return [fetch_release_entity(id) for id in ids]



