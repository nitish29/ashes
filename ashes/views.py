from urllib.request import Request, urlopen
#import urllib.parse
#import json
from django.shortcuts import render
from django.conf import settings
import pdb
from .models import PlayerStats, UserPlayers


def home(request):
	try:
		errors = []
		#pdb.set_trace()

		players = PlayerStats.objects.all()
		userPlayers = UserPlayers.objects.all()
		# print(players)

		# for player in players:
		# 	print(player.player_name)

		# for myplayer in userPlayers:
		# 	print(myplayer.player_name.player_name)

		context = {'allPlayerList': players, 'myPlayerList': userPlayers}

	except:
		
		errors.append('Error Completing request')
		context = {'errors': errors}

	return render(request, "playercompare.html", context)


def playerCompareAction(request):
	try:
		errors = []
		if request.GET['myPlayerSelect']:
			my_player = UserPlayers.objects.get(player_name=request.GET['myPlayerSelect'])
		if request.GET['allPlayerSelect']:
			other_player = PlayerStats.objects.get(player_name=request.GET['allPlayerSelect'])

		my_player_caa = my_player.player_name.caa
		other_player_caa = other_player.caa

		if my_player_caa > other_player_caa:
			message = 'We recommend ' + my_player.player_name.player_name + ' over ' + other_player.player_name
			print(message)
		else:
			message = 'We recommend ' + other_player.player_name + ' over ' + my_player.player_name.player_name
			print(message)

		players = PlayerStats.objects.all()
		userPlayers = UserPlayers.objects.all()
		
		context = {'allPlayerList': players, 'myPlayerList': userPlayers, 'myPlayer': my_player, 'otherPlayer': other_player, 'message': message}

	except:
		errors.append('Error Completing request')
		context = {'errors': errors}

	return render(request, "playercompare.html", context)