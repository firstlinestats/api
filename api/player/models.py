from __future__ import unicode_literals

from django.db import models

import constants


class Player(models.Model):
    id = models.IntegerField(primary_key=True)
    fullName = models.CharField(max_length=100)
    link = models.URLField()
    firstName = models.CharField(max_length=50)
    lastName = models.CharField(max_length=50)
    primaryNumber = models.IntegerField(null=True, blank=True)
    primaryPositionCode = models.CharField(max_length=1, choices=constants.playerPositions)
    birthDate = models.DateField()
    birthCity = models.CharField(max_length=100)
    birthStateProvince = models.CharField(max_length=100)
    birthCountry = models.CharField(max_length=100)
    height = models.CharField(max_length=10)
    weight = models.IntegerField()
    active = models.BooleanField(default=True)
    rookie = models.BooleanField(default=False)
    shootsCatches = models.CharField(max_length=1, blank=True, null=True)
    rosterStatus = models.CharField(max_length=1, choices=constants.rosterChoices)
    currentTeam = models.ForeignKey("team.Team", blank=True, null=True)

    def __unicode__(self):
        return self.fullName


class CompiledPlayerGameStats(models.Model):
    player = models.ForeignKey(Player)
    game = models.ForeignKey("playbyplay.Game")
    period = models.IntegerField(db_index=True)
    strength = models.CharField(max_length=4, db_index=True)
    goals = models.IntegerField()  # Individual Goals
    assists = models.IntegerField()  # Individual Assists
    assists2 = models.IntegerField()  # Individual Sec. Assists
    gf = models.IntegerField()  # On-Ice Goals For
    ga = models.IntegerField()  # On-Ice Goals Against
    pnDrawn = models.IntegerField()
    pn = models.IntegerField()
    sf = models.IntegerField()  # Personal Shots For
    msf = models.IntegerField()  # Personal Missed Shots For
    bsf = models.IntegerField()  # Personal Blocked Shots For
    ab = models.IntegerField()  # Shot Attempts Blocked By Player
    onsf = models.IntegerField()  # On-Ice Shots For
    onmsf = models.IntegerField()  # On-Ice Missed Shots For
    onbsf = models.IntegerField()  # On-Ice Blocked Shots For
    offgf = models.IntegerField()  # Off-Ice Goals For
    offsf = models.IntegerField()  # Off-Ice Shots For
    offmsf = models.IntegerField()  # Off-Ice Missed Shots For
    offbsf = models.IntegerField()  # Off-Ice Blocked Shots For
    offga = models.IntegerField()  # Off-Ice Goals Against
    offsa = models.IntegerField()  # Off-Ice Shots Against
    offmsa = models.IntegerField()  # Off-Ice Missed Shots Against
    offbsa = models.IntegerField()  # Off-Ice Blocked Shots Against
    sa = models.IntegerField()  # Shots Against
    msa = models.IntegerField()  # Missed Shots Against
    bsa = models.IntegerField()  # Blocked Shots Against
    zso = models.IntegerField()  # Offensive Zone Starts
    zsn = models.IntegerField()  # Neutral Zone Starts
    zsd = models.IntegerField() # Defensive Zone Starts
    toi = models.TimeField()
    timeOffIce = models.TimeField()
    ihsc = models.IntegerField()  # Individual High-Danger Scoring Chances
    isc = models.IntegerField()  # Individual Scoring Chances
    sc = models.IntegerField()  # Scoring Chances
    hscf = models.IntegerField()  # High-Danger Scoring Chances
    hsca = models.IntegerField()  # HSC Against
    sca = models.IntegerField()  # SC Against
    fo_w = models.IntegerField()  # Faceoffs Won
    fo_l = models.IntegerField()  # Faceoffs Lost
    hit = models.IntegerField()  # Hits
    hitt = models.IntegerField()  # Hits Taken
    gv = models.IntegerField()  # Giveaways
    tk = models.IntegerField()  # Takeaways


class CompiledGoalieGameStats(models.Model):
    player = models.ForeignKey(Player)
    game = models.ForeignKey("playbyplay.Game")
    period = models.IntegerField(db_index=True)
    strength = models.CharField(max_length=4, db_index=True)
    shotsLow = models.IntegerField()
    savesLow = models.IntegerField()
    shotsMedium = models.IntegerField()
    savesMedium = models.IntegerField()
    shotsHigh = models.IntegerField()
    savesHigh = models.IntegerField()
    toi = models.TimeField()
