from django.db import models

class PlayerStats(models.Model):
    total_runs = models.IntegerField(default=0, null=True)
    total_outs = models.IntegerField(default=0, null=True)
    innings = models.IntegerField(default=0, null=True)
    player_name = models.CharField(max_length=150, primary_key=True)
    batting_impact_list = models.CharField(max_length=500, null=True)
    runs_in_matches = models.CharField(max_length=500, null=True)
    tag = models.CharField(max_length=50, null=True)
    batting_avg = models.FloatField(default=0, null=True)
    caa = models.FloatField(default=0, null=True)
    last_bat_impact = models.FloatField(default=0, null=True)
    team_name = models.CharField(max_length=100, null=True)
    player_match_name = models.CharField(max_length=100, null=True)
    
class UserPlayers(models.Model):
    player_name = models.ForeignKey(PlayerStats)
    search_target = models.CharField(max_length=100, null=True)
    articles_search_target = models.CharField(max_length=100, null=True)



class PlayerMatchData(models.Model):
    status = models.CharField(max_length=500, null=True)
    runs = models.CharField(max_length=10, null=True)
    tournament = models.CharField(max_length=500, null=True)
    balls_faced = models.CharField(max_length=10, null=True)
    match_date = models.DateField()
    player_name = models.ForeignKey(PlayerStats)
    fours = models.CharField(max_length=10, null=True)
    six = models.CharField(max_length=10, null=True)
    team_name = models.CharField(max_length=100, null=True)
    opponent_team_name = models.CharField(max_length=100, null=True)
    strike_rate = models.CharField(max_length=10, null=True)
    match_status = models.CharField(max_length=500, null=True)
    caa = models.FloatField(default=0, null=True)
    last_bat_impact = models.FloatField(default=0, null=True)
