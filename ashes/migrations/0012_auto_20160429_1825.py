# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-29 18:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ashes', '0011_auto_20160429_1824'),
    ]

    operations = [
        migrations.AlterField(
            model_name='playerstats',
            name='other_player',
            field=models.BooleanField(default=False),
        ),
    ]