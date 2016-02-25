# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-24 20:16
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('playbyplay', '0001_initial'),
        ('team', '0001_initial'),
        ('player', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='playeronice',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='player.Player'),
        ),
        migrations.AddField(
            model_name='playerinplay',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playbyplay.Game'),
        ),
        migrations.AddField(
            model_name='playerinplay',
            name='play',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playbyplay.PlayByPlay'),
        ),
        migrations.AddField(
            model_name='playerinplay',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='player.Player'),
        ),
        migrations.AddField(
            model_name='playergamestats',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playbyplay.Game'),
        ),
        migrations.AddField(
            model_name='playergamestats',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='player.Player'),
        ),
        migrations.AddField(
            model_name='playergamestats',
            name='team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='team.Team'),
        ),
        migrations.AddField(
            model_name='playbyplay',
            name='gamePk',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playbyplay.Game'),
        ),
        migrations.AddField(
            model_name='playbyplay',
            name='team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='team.Team'),
        ),
        migrations.AddField(
            model_name='goaliegamestats',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playbyplay.Game'),
        ),
        migrations.AddField(
            model_name='goaliegamestats',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='player.Player'),
        ),
        migrations.AddField(
            model_name='goaliegamestats',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='team.Team'),
        ),
        migrations.AddField(
            model_name='gamescratch',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playbyplay.Game'),
        ),
        migrations.AddField(
            model_name='gamescratch',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='player.Player'),
        ),
        migrations.AddField(
            model_name='gamescratch',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='team.Team'),
        ),
        migrations.AddField(
            model_name='gameperiod',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playbyplay.Game'),
        ),
        migrations.AddField(
            model_name='game',
            name='awayTeam',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='awayTeam', to='team.Team'),
        ),
        migrations.AddField(
            model_name='game',
            name='firstStar',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='firstStar', to='player.Player'),
        ),
        migrations.AddField(
            model_name='game',
            name='homeTeam',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='homeTeam', to='team.Team'),
        ),
        migrations.AddField(
            model_name='game',
            name='secondStar',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='secondStar', to='player.Player'),
        ),
        migrations.AddField(
            model_name='game',
            name='thirdStar',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='thirdStar', to='player.Player'),
        ),
        migrations.AddField(
            model_name='game',
            name='venue',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='team.Venue'),
        ),
        migrations.AlterUniqueTogether(
            name='playeronice',
            unique_together=set([('play', 'player')]),
        ),
    ]
