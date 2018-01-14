"""
Look up a name in a set of named world map locations JSON files,
and show the city/region/country and current time

JSON files go in data/*.json, and are lists of records like:

[{"city": "Vancouver",
  "cty": "CA",
  "lat": 49.2827,
  "lng": -123.1207,
  "nm": "an awesome place"},
 ...
]
"""
import argparse
import json
import os
import pprint
import urllib
import webbrowser

import datetime
import pytz
import reverse_geocoder
import timezonefinder

script_path = os.path.dirname(os.path.abspath(__file__))


def get_coordinates(entry):
    return entry["lat"], entry["lng"]


def json_contents(filename):
    with open(filename, "r") as handle:
        cur_list = json.load(handle)
    return cur_list


class GeoData(object):
    def __init__(self):
        self.data_dir = os.path.join(script_path, "data")

        self.entries_by_name = {}
        self.names = []

        for filename_proper in os.listdir(self.data_dir):
            if not filename_proper.lower().endswith(".json"):
                continue

            filename = os.path.join(self.data_dir, filename_proper)
            cur_list = json_contents(filename)

            for entry in cur_list:
                name = entry["nm"]
                # pprint.pprint(entry)
                self.entries_by_name.setdefault(name, []).append(entry)
                self.names.append(name)

    def find_matching_names(self, substr):
        substr = substr.lower()
        if substr == "":
            for name in self.names:
                yield name
        else:
            for name in self.names:
                if substr in name.lower():
                    yield name

    def get_entries_for_name(self, name):
        return self.entries_by_name[name]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("query",
                        help="text fragment to search for"
                        )
    parser.add_argument("--json",
                        help="show the JSON of the matching records",
                        default=False,
                        action="store_true"
                        )
    parser.add_argument("--all",
                        help="show all matching entries",
                        dest="dupes",
                        default=False,
                        action="store_true",
                        )
    parser.add_argument("--browse",
                        help="open a map of the location in a browser",
                        default=False,
                        action="store_true",
                        )
    return parser.parse_args()


def get_google_maps_url(coordinates, text=None):
    ll_text = "%s,%s" % coordinates
    if text is not None:
        q = text
    else:
        q = ll_text
    q = urllib.quote(q)
    # TBD how to get google to show our database place name as a map marker
    return "https://www.google.com/maps/place/%s/@%s,5z" % (ll_text, ll_text)


def main():
    options = parse_args()
    g = GeoData()

    country_code_lookup = load_countries()

    dupes = set()

    for name in g.find_matching_names(options.query):
        if not options.dupes:
            name_key = name.lower()
            if name_key in dupes:
                continue
            else:
                dupes.add(name_key)

        for entry in g.get_entries_for_name(name):
            if options.json:
                pprint.pprint(entry)
            city = entry.get("city")
            country_code = entry.get("cty")

            text = name
            if city and country_code:
                text += ", %s, %s" % (city, country_code)

            coordinates = get_coordinates(entry)

            if country_code in country_code_lookup:
                country_display = country_code_lookup[country_code]
            else:
                country_display = country_code

            if options.browse:
                map_url = get_google_maps_url(coordinates, text)
                webbrowser.open(map_url)

            results = reverse_geocoder.search(coordinates)

            if len(results) > 0:
                result = results[0]
                print result
                country_code = result.get("cc")
                country_display = country_code_lookup[country_code]
                place = "%s, %s, %s, %s" % (city, result.get("admin2"), result.get("admin1"), country_display)
            else:
                place = "%s, %s" % (city, country_display)
            print u"%s is in %s" % (name, place)

            tf = timezonefinder.TimezoneFinder()
            timezone_str = tf.certain_timezone_at(lat=coordinates[0], lng=coordinates[1])
            if timezone_str is None:
                print "Could not determine the time zone"
            else:
                timezone = pytz.timezone(timezone_str)
                dt = datetime.datetime.utcnow()
                offset = timezone.utcoffset(dt)
                print "The time in %s is %s (UTC%s)" % (timezone_str, dt + offset, utc_offset_str(offset))

            if not options.dupes:
                break


def utc_offset_str(offset):
    """
    Show the given time offset as a string in the conventional form for the time part of a UTC offset
    :rtype: str
    """
    assert isinstance(offset, datetime.timedelta)
    offset_mins = offset.total_seconds() / 60
    if offset_mins > 0:
        offset_form = "+%02d:%02d"
    else:
        offset_form = "-%02d:%02d"
        offset_mins = -offset_mins
    offset_str = offset_form % (offset_mins / 60, offset_mins % 60)
    return offset_str


def load_countries():
    country_code_lookup = {}
    countries = json_contents(os.path.join(script_path, "countries.json"))
    for entry in countries:
        code = entry["code"]
        name = entry["name"]
        country_code_lookup[code] = name
    return country_code_lookup


if __name__ == "__main__":
    main()
