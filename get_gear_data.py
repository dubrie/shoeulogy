from shoeulogy import strava_oauth2, Shoeulogy
import os
import config
import re
from loguru import logger 

METERS_TO_FEET_RATIO = 3.28084
METERS_TO_MILES_RATIO = 0.0006213712121212121   # 3.28084 / 5280

activity_url = input("Post the URL for your last activity with your shoes: ")
pattern_match = re.search(r"[0-9]*$", activity_url)
activity_id = pattern_match.group()
logger.debug("Activity ID: " + activity_id)

if "STRAVA_ACCESS_TOKEN" not in os.environ:
    token = strava_oauth2(client_id=config.stravaConfig.client_id, client_secret=config.stravaConfig.client_secret)
    os.environ["STRAVA_ACCESS_TOKEN"]=token["access_token"]
    os.environ["STRAVA_REFRESH_TOKEN"]=token["refresh_token"]

client = Shoeulogy()

euolgy_activity = client.get_activity_by_id(activity_id)
gear_id = euolgy_activity.gear.id
logger.debug(euolgy_activity.gear.name + " (" + gear_id + ")")

athlete_response = client.get_logged_in_athlete()
athlete = athlete_response.to_dict()
activities_after = athlete['created_at']

# Get All Activities that have this gear id set.
activities_list = client.get_logged_in_athlete_activities(after=activities_after)

# Initialize values for tracking categories
count = 0
first_activity = None 
last_activity = None
medals = 0
trophies = 0
crowns = 0
legends = 0
photos = []
kudos = 0
calories = 0
distance = 0
elevation = 0
duration = 0
activity_links = []

print ("Generating stats for your " + euolgy_activity.gear.name)
for activity in activities_list:
    if activity.gear_id == gear_id:
        count += 1

        activity_detail = client.get_activity_by_id(activity.id)

        logger.debug("https://www.strava.com/activities/" + str(activity.id))
        kudos += activity_detail.kudos_count
        if hasattr(activity_detail, 'calories'):
            calories += activity_detail.calories
        distance += activity_detail.distance
        duration += activity_detail.elapsed_time
        elevation += activity_detail.total_elevation_gain

        if first_activity is None:
            first_activity = activity_detail.start_date
        last_activity = activity_detail.start_date
        
        if activity_detail.achievement_count > 0:

            if hasattr(activity_detail, 'segment_efforts'):
                for effort in activity_detail.segment_efforts:
                    if effort.pr_rank == 1:
                        medals += 1
                    if effort.kom_rank is not None:
                        if effort.kom_rank == 1:
                            crowns += 1
                        else:
                            trophies += 1
    else:
        continue

# Clean up some of the output
distance_miles = "{:,.1f}".format(distance * METERS_TO_MILES_RATIO)
elevation_feet = "{:,.1f}".format(elevation * METERS_TO_FEET_RATIO)
kudos_format = "{:,}".format(kudos)
time_hours = "{:,.1f}".format(duration / 60 / 60)
calories_format = "{:,.0f}".format(calories)

print("Shoeulogy for " + euolgy_activity.gear.name)
print(first_activity.strftime('%b %d, %Y') + " - " + last_activity.strftime('%b %d, %Y'))
print("")
print("Stats:")
print("Total Activities: " + str(count))
print("Miles: " + str(distance_miles) + " mi")
print("Seggy PRs: " + str(medals))
print("Seggy Trophs: " + str(trophies))
print("Seggy Crowns: " + str(crowns))
print("Total Elevation Climbed: " + str(elevation_feet) + " ft")
print("Total Kudos: " + str(kudos_format))
print("Total Duration: " + str(time_hours) + " hours")
print("Total Calories Burned: " + str(calories_format))

exit(0)