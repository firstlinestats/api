

gameTypes = (
    ("PR", "Pre-season"),
    ("R", "Regular season"),
    ("P", "Playoffs"),
    ("A", "All-Star game")
)

gameStates = (
    ("1", "Preview (Scheduled)"),
    ("2", "Preview (Pre-Game)"),
    ("3", "Live (In Progress)"),
    ("4", "Live (In Progress - Critical)"),
    ("5", "Final (Game Over)"),
    ("6", "Final"),
    ("7", "Final"),
    ("8", "Preview (Scheduled (Time TBD))"),
    ("9", "Preview (Postponed)")
)

playerTypes = (
    (0, "Unknown"),
    (1, "Winner"),
    (2, "Loser"),
    (3, "Hitter"),
    (4, "Hittee"),
    (5, "Scorer"),
    (6, "Assist"),
    (7, "Shooter"),
    (8, "Goalie"),
    (9, "Blocker"),
    (10, "PenaltyOn"),
    (11, "DrewBy"),
    (12, "ServedBy"),
    (13, "PlayerID"),
    (14, "Fighter"),
    (15, "OnIce"),
    (16, "Assist 2")
)

playTypes = (
    ("UNKNOWN", "Unknown"),
    ("FACEOFF", "Faceoff"),
    ("HIT", "Hit"),
    ("GIVEAWAY", "Giveaway"),
    ("GOAL", "Goal"),
    ("SHOT", "Shot"),
    ("MISSED_SHOT", "Missed Shot"),
    ("PENALTY", "Penalty"),
    ("PENALTY_END", "Penalty Ended"),
    ("STOP", "Stoppage"),
    ("SUBSTITUTION", "Substitution"),
    ("FIGHT", "Fight"),
    ("TAKEAWAY", "Takeaway"),
    ("BLOCKED_SHOT", "Blocked Shot"),
    ("PERIOD_START", "Period Start"),
    ("PERIOD_END", "Period End"),
    ("GAME_END", "Game End"),
    ("GAME_SCHEDULED", "Game Scheduled"),
    ("PERIOD_READY", "Period Ready"),
    ("PERIOD_OFFICIAL", "Period Official"),
    ("SHOOTOUT_COMPLETE", "Shootout Complete"),
    ("EARLY_INT_START", "Early Intermission Start"),
    ("EARLY_INT_END", "Early Intermission End"),
    ("GAME_OFFICIAL", "Game Official"),
    ("CHALLENGE", "Official Challenge"),
    ("EMERGENCY_GOALTENDER", "Emergency Goaltender"),
)

shotTypes = (
    ("WRIST", "Wrist"),
    ("SNAP", "Snapshot"),
    ("SLAP", "Slapshot"),
    ("BACK", "Backhand"),
    ("TIP", "Tip-In"),
    ("WRAP", "Wrap"),
    ("DEFLECT", "Deflected"),
    ("UNSPECIFIED", "Unspecified")
)

teamNames = (
    (21, 'Avalanche'),
    (16, 'Blackhawks'),
    (29, 'Blue Jackets'),
    (19, 'Blues'),
    (6, 'Bruins'),
    (8, 'Canadiens'),
    (23, 'Canucks'),
    (15, 'Capitals'),
    (53, 'Coyotes'),
    (1, 'Devils'),
    (24, 'Ducks'),
    (20, 'Flames'),
    (4, 'Flyers'),
    (12, 'Hurricanes'),
    (2, 'Islanders'),
    (52, 'Jets'),
    (26, 'Kings'),
    (14, 'Lightning'),
    (10, 'Maple Leafs'),
    (22, 'Oilers'), 
    (13, 'Panthers'), 
    (5, 'Penguins'), 
    (18, 'Predators'), 
    (3, 'Rangers'), 
    (17, 'Red Wings'), 
    (7, 'Sabres'), 
    (9, 'Senators'), 
    (28, 'Sharks'), 
    (25, 'Stars'), 
    (30, 'Wild')
)

homeAway = (
    (0, "Home"),
    (1, "Away"),
    (2, "All")
)
