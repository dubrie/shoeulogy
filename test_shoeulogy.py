from shoeulogy import strava_oauth2, Shoeulogy
import os
import config

# Get oauth access for Strava
if "STRAVA_ACCESS_TOKEN" not in os.environ:
    token = strava_oauth2(client_id=config.stravaConfig.client_id, client_secret=config.stravaConfig.client_secret)
    os.environ["STRAVA_ACCESS_TOKEN"]=token["access_token"]
    os.environ["STRAVA_REFRESH_TOKEN"]=token["refresh_token"]

# Create Shoeulogy client.
#    This manages all the Strava API connectivity and Shoeulogy business logic
client = Shoeulogy()

athlete = client.get_logged_in_athlete()
athlete_dict = athlete.to_dict()

activities = client.get_logged_in_athlete_activities(after='last month')

# Collect all gear used over the last month of your activities
gear_dict = {}
for act in activities:
    gear_info = {}
    if act.gear_id not in gear_dict:
        if act.gear_id is not None:
            gear_info = client.get_gear_by_id(act.gear_id)
        else:
            continue
    else:
        gear_info = gear_dict[act.gear_id]

    gear_info.activities.append(act.id)
    gear_dict[act.gear_id] = gear_info

print(gear_dict)
exit(0)