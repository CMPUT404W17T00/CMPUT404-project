# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-13 06:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='remotenode',
            name='localToRemotePassword',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='remotenode',
            name='localToRemoteUserName',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='remotenode',
            name='remoteToLocalPassword',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='remotenode',
            name='remoteToLocalUsername',
            field=models.CharField(max_length=64),
        ),
    ]
