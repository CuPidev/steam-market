# Objective: match listing hashes with badge creation details.

import random

from market_listing import get_item_nameid_batch
from market_search import load_all_listings, update_all_listings
from parsing_utils import parse_badge_creation_details
from sack_of_gems import get_gem_price
from utils import convert_listing_hash_to_app_id, convert_listing_hash_to_app_name


def determine_whether_listing_hash_is_dubious(listing_hash):
    dubious_str = '#Economy_TradingCards_'

    listing_hash_is_dubious = bool(dubious_str in listing_hash)

    return listing_hash_is_dubious


def filter_out_dubious_listing_hashes(all_listings,
                                      verbose=True):
    # Filter out listing hashes which hint at a dubious market listing for the booster pack. For instance:
    #   362680-Fran Bow #Economy_TradingCards_ItemType_BoosterPack
    #   844870-#Economy_TradingCards_Type_GameType

    filtered_listings = dict()

    for listing_hash in all_listings.keys():
        individual_market_listing = all_listings[listing_hash]

        booster_pack_is_dubious = determine_whether_listing_hash_is_dubious(listing_hash)

        if not booster_pack_is_dubious:
            filtered_listings[listing_hash] = individual_market_listing
        else:
            if verbose:
                print('Omitting dubious listing hash: {}'.format(listing_hash))

    if verbose:
        print('There are {} seemingly valid market listings. ({} omitted because of a dubious listing hash)'.format(
            len(filtered_listings), len(all_listings) - len(filtered_listings)))

    return filtered_listings


def match_badges_with_listing_hashes(badge_creation_details=None,
                                     all_listings=None,
                                     verbose=True):
    # Badges for games which I own

    if badge_creation_details is None:
        badge_creation_details = parse_badge_creation_details()

    badge_app_ids = list(badge_creation_details.keys())

    # Listings for ALL the existing Booster Packs

    if all_listings is None:
        all_listings = load_all_listings()

    all_listing_hashes = list(all_listings.keys())

    # Dictionaries to match appIDs or app names with listing hashes

    listing_matches_with_app_ids = dict()
    listing_matches_with_app_names = dict()
    for listing_hash in all_listing_hashes:
        app_id = convert_listing_hash_to_app_id(listing_hash)
        app_name = convert_listing_hash_to_app_name(listing_hash)

        listing_matches_with_app_ids[app_id] = listing_hash
        listing_matches_with_app_names[app_name] = listing_hash

    # Match badges with listing hashes

    badge_matches = dict()
    for app_id in badge_app_ids:
        app_name = badge_creation_details[app_id]['name']

        try:
            badge_matches[app_id] = listing_matches_with_app_ids[app_id]
        except KeyError:

            try:
                badge_matches[app_id] = listing_matches_with_app_names[app_name]
                if verbose:
                    print('Match for {} (appID = {}) with name instead of id.'.format(app_name, app_id))
            except KeyError:
                badge_matches[app_id] = None
                if verbose:
                    print('No match found for {} (appID = {})'.format(app_name, app_id))

    if verbose:
        print('#badges = {} ; #matching hashes found = {}'.format(len(badge_app_ids), len(badge_matches)))

    return badge_matches


def aggregate_badge_data(badge_creation_details,
                         badge_matches,
                         all_listings=None,
                         enforced_sack_of_gems_price=None,
                         minimum_allowed_sack_of_gems_price=None,
                         retrieve_gem_price_from_scratch=False):
    # Aggregate data:
    #       owned appID --> (gem PRICE, sell price)
    # where:
    # - the gem price is the price required to buy gems on the market to then craft a booster pack for this game,
    # - the sell price is the price which sellers are asking for this booster pack.
    #
    # NB: ensure the same currency is used.

    if all_listings is None:
        all_listings = load_all_listings()

    gem_price = get_gem_price(enforced_sack_of_gems_price=enforced_sack_of_gems_price,
                              minimum_allowed_sack_of_gems_price=minimum_allowed_sack_of_gems_price,
                              retrieve_gem_price_from_scratch=retrieve_gem_price_from_scratch)

    badge_app_ids = list(badge_creation_details.keys())

    aggregated_badge_data = dict()

    for app_id in badge_app_ids:
        app_name = badge_creation_details[app_id]['name']
        gem_amount_required_to_craft_booster_pack = badge_creation_details[app_id]['gem_value']
        try:
            next_creation_time = badge_creation_details[app_id]['next_creation_time']
        except KeyError:
            next_creation_time = None
        listing_hash = badge_matches[app_id]

        if listing_hash is None:
            # For some reason for Conran - The dinky Raccoon (appID = 612150), there is no listing of any "Booster Pack"
            # Reference: https://steamcommunity.com/market/search?appid=753&category_753_Game%5B0%5D=tag_app_612150
            continue
        else:
            sell_price_in_cents = all_listings[listing_hash]['sell_price']
            sell_price_in_euros = sell_price_in_cents / 100

        aggregated_badge_data[app_id] = dict()
        aggregated_badge_data[app_id]['name'] = app_name
        aggregated_badge_data[app_id]['listing_hash'] = listing_hash
        aggregated_badge_data[app_id]['gem_amount'] = gem_amount_required_to_craft_booster_pack
        aggregated_badge_data[app_id]['gem_price'] = gem_amount_required_to_craft_booster_pack * gem_price
        aggregated_badge_data[app_id]['sell_price'] = sell_price_in_euros
        aggregated_badge_data[app_id]['next_creation_time'] = next_creation_time

    return aggregated_badge_data


def load_aggregated_badge_data(retrieve_listings_from_scratch=False,
                               enforced_sack_of_gems_price=None,
                               minimum_allowed_sack_of_gems_price=None,
                               from_javascript=False):
    badge_creation_details = parse_badge_creation_details(from_javascript=from_javascript)

    if retrieve_listings_from_scratch:
        update_all_listings()

    all_listings = load_all_listings()

    all_listings = filter_out_dubious_listing_hashes(all_listings)

    badge_matches = match_badges_with_listing_hashes(badge_creation_details,
                                                     all_listings)

    retrieve_gem_price_from_scratch = bool(enforced_sack_of_gems_price is None)

    aggregated_badge_data = aggregate_badge_data(badge_creation_details,
                                                 badge_matches,
                                                 all_listings=all_listings,
                                                 enforced_sack_of_gems_price=enforced_sack_of_gems_price,
                                                 minimum_allowed_sack_of_gems_price=minimum_allowed_sack_of_gems_price,
                                                 retrieve_gem_price_from_scratch=retrieve_gem_price_from_scratch)

    return aggregated_badge_data


def populate_random_samples_of_badge_data(badge_data=None, num_samples=50):
    if badge_data is None:
        badge_data = load_aggregated_badge_data()

    listing_hashes = [badge_data[app_id]['listing_hash'] for app_id in badge_data.keys()]

    num_samples = min(num_samples, len(listing_hashes))

    listing_hash_samples = [listing_hashes[i]
                            for i in random.sample(range(len(listing_hashes)), k=num_samples)]

    item_nameids = get_item_nameid_batch(listing_hash_samples)

    return True


def main(populate_all_item_name_ids=False):
    if populate_all_item_name_ids:
        # Pre-retrieval of ALL of the MISSING item name ids.
        # Caveat: this may require a long time, due to API rate limits.

        all_listings = load_all_listings()
        item_nameids = get_item_nameid_batch(listing_hashes=all_listings)

    else:
        aggregated_badge_data = load_aggregated_badge_data()
        populate_random_samples_of_badge_data(aggregated_badge_data, num_samples=50)

    return True


if __name__ == '__main__':
    main(populate_all_item_name_ids=False)
