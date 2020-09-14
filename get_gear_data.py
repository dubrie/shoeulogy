from shoeulogy import strava_oauth2, Shoeulogy
import os
import config
import re
from loguru import logger 

skip = True
METERS_TO_MILES_RATIO = 0.0006213712121212121   # 3.28084 / 5280

if not skip:
    activity_url = input("Post the URL for your last activity with your shoes: ")
    pattern_match = re.search(r"[0-9]*$", activity_url)
    activity_id = pattern_match.group()
    logger.debug("Activity ID: " + activity_id)
else:
    # Debug ID
    activity_id = 4013245395
    logger.debug("Activity ID [debug]: {activity_id}")


if "STRAVA_ACCESS_TOKEN" not in os.environ:
    token = strava_oauth2(client_id=config.stravaConfig.client_id, client_secret=config.stravaConfig.client_secret)
    os.environ["STRAVA_ACCESS_TOKEN"]=token["access_token"]
    os.environ["STRAVA_REFRESH_TOKEN"]=token["refresh_token"]

client = Shoeulogy()

euolgy_activity = client.get_activity_by_id(activity_id)
gear_id = euolgy_activity.gear.id
logger.debug(euolgy_activity)
logger.debug(gear_id)
logger.debug(euolgy_activity.gear.name)

athlete_response = client.get_logged_in_athlete()
athlete = athlete_response.to_dict()
logger.debug("Athlete created: ")
logger.debug(athlete['created_at'])

if not skip:
    activities_after = athlete['created_at']
else:
    activities_after = "3 years ago" 

# Get All Activities that have this gear id set.
activities_list = client.get_logged_in_athlete_activities(after=activities_after)

# Collect:
#     Date
#     Achievements
#     Trophies
#     Photos
#     Locations
#     Total Kudos
#     Total Calories
#     Total Distance
#     Total Time
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
            logger.debug("Achievements")
            logger.debug(activity_detail.achievement_count)

            if hasattr(activity_detail, 'segment_efforts'):
                for effort in activity_detail.segment_efforts:
                    logger.debug("Effort: " + effort.name)
                    if effort.pr_rank == 1:
                        medals += 1
                    if effort.kom_rank is not None:
                        if effort.kom_rank == 1:
                            crowns += 1
                        else:
                            trophies += 1
    else:
        continue

distance_miles = distance

logger.debug("Number of activities: ")
logger.debug(count)

logger.debug("Shoeulogy for " + euolgy_activity.gear.name)
logger.debug(first_activity.strftime('%b %d, %Y') + " - " + last_activity.strftime('%b %d, %Y'))
logger.debug("")
logger.debug("Stats:")
logger.debug("Total Activities: " + str(count))
logger.debug("Miles: " + str(distance * METERS_TO_MILES_RATIO))
logger.debug("Seggy PRs: " + str(medals))
logger.debug("Seggy Trophs: " + str(trophies))
logger.debug("Seggy Crowns: " + str(crowns))
logger.debug("Total Calories Burned: " + str(calories))
logger.debug("Total Elevation Climbed: " + str(elevation))
logger.debug("Total Kudos: " + str(kudos))
logger.debug("Total Duration: " + str(duration))

