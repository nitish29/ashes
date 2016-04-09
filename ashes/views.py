from urllib.request import Request, urlopen
#import urllib.parse
#import json
from django.shortcuts import render
from django.conf import settings
import pdb
from .models import PlayerStats


def home(request):
	try:
		errors = []
		pdb.set_trace()

		players = PlayerStats.objects.all()
		# print(players)

		for player in players:
			print(player.player_name)



		#data_fetched_from_api = fetchEventbriteCategories()

	# 	if data_fetched_from_api['status'] == "success":

	# 		categories = data_fetched_from_api['data']["categories"]	

	# 	else:
			
	# 		errors.append(data_fetched_from_api['errors'])
	# 		raise Exception(errors)

	# 	if not errors:
			
	# 		context = { 'categories' : categories }
			
	# 	else:
			
	# 		errors.append('Error fetching API details')
	# 		raise Exception(errors)

	except:
		
		errors.append('Error Completing request')
	# 	context = { 'errors' : errors }

	return render(request, "categories.html")