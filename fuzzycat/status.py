from enum import Enum

class MatchStatus(Enum):
    """
    When matching two entities, use these levels to express match strength.
    When in doubt, use AMBIGIOUS. DIFFERENT should be used only, when it is
    certain, that items do not match.
    """

    EXACT = 0
    STRONG = 1
    WEAK = 2
    AMBIGIOUS = 3
    DIFFERENT = 4
