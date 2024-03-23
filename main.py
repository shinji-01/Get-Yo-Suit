import asyncio
import copy
import os
import re
import json
import httpx

CAPTURE_SIZE_REGEX = '[^0-9\n]*(\d+,?\.?\d?)'

async def get_items():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        await client.get("https://vinted.fr")
        res = await client.get("https://vinted.fr/api/v2/users/80166736/items?page=1&per_page=1000&order=newest_first")
        items = res.json().get("items", [])

        return items


def get_config():
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
        config = json.loads(f.read())

        return config


def format_size(size):
    if size is not None:
        return float(size.replace(",", "."))

    return None



def get_shoulder_width(content):
    m = re.search(rf"largeur (?:d')?épaule{CAPTURE_SIZE_REGEX}", content, flags=re.IGNORECASE)

    if m is not None:
        size = m.group(1)


        return format_size(size)

    return None


def get_jacket_length(content):
    m = re.search(rf"longueur.*?(?:total|veste){CAPTURE_SIZE_REGEX}", content, flags=re.IGNORECASE)

    if m is not None:
        size = m.group(1)

        return format_size(size)

    return None


def get_sleeves_length(content):
    m = re.search(rf"longueur.*?manche{CAPTURE_SIZE_REGEX}", content, flags=re.IGNORECASE)

    if m is not None:
        size = m.group(1)

        return format_size(size)

    return None


def get_leg_opening(content):
    m = re.search(rf"ouverture.*?jambe{CAPTURE_SIZE_REGEX}", content, flags=re.IGNORECASE)

    if m is not None:
        size = m.group(1)

        return format_size(size)

    return None


def get_fork_height(content):
    m = re.search(rf"hauteur.*?fourche{CAPTURE_SIZE_REGEX}", content, flags=re.IGNORECASE)

    if m is not None:
        size = m.group(1)

        return format_size(size)

    return None


def get_pants_width(content):
    m = re.search(rf"largeur.*?niveau.*?taille{CAPTURE_SIZE_REGEX}{CAPTURE_SIZE_REGEX}?", content, flags=re.IGNORECASE)

    if m is not None:
        size = m.group(1)
        margin = m.group(2)

        return format_size(size), format_size(margin)

    return None, None


def get_pants_length(content):
    m = re.search(rf"longueur.*?pantalon{CAPTURE_SIZE_REGEX}", content, flags=re.IGNORECASE)

    if m is not None:
        size = m.group(1)

        return format_size(size)

    return None


def filter_values(obj):
    res = {}

    for field in obj:
        if obj.get(field) is not None:
            res.update({
                field: obj.get(field)
            })

    return res

def get_range(value):
    low, high = value.split('-')

    return format_size(low), format_size(high)

def is_in_range(low, high, value):
    return min(low, high) < value < max(low, high)


def match_config(jacket, pants, config):
    jacket_config = config.get("jacket")
    pants_config = config.get("pants")

    jacket_result = copy.deepcopy(jacket)
    pants_result = copy.deepcopy(pants)

    if jacket:
        for field in jacket:
            low, high = get_range(jacket_config.get(field))
            jacket_result[field] = is_in_range(low, high, jacket.get(field))

    if pants:
        for field in pants:
            low, high = get_range(pants_config.get(field))
            pants_result[field] = is_in_range(low, high, pants.get(field))


    return jacket_result, pants_result

def do_match(matches):
    if matches:
        for field in matches:
            if not matches.get(field):
                return False

        return True
    else:
        return False


async def main():
    items = await get_items()
    config = get_config()

    for item in items:
        description = item.get("description")

        jacket = {
            "shoulders": get_shoulder_width(description),
            "sleeves": get_sleeves_length(description),
            "length": get_jacket_length(description),
        }

        width, width_margin = get_pants_width(description)

        pants = {
            "fork": get_fork_height(description),
            "leg_opening": get_leg_opening(description),
            "length": get_pants_length(description),
            "width": width,
            # "width_margin": width_margin,
        }

        jacket = filter_values(jacket)
        pants = filter_values(pants)

        jacket_matches, pants_matches = match_config(jacket, pants, config)


        do_jacket_match = do_match(jacket_matches)
        do_pants_match = do_match(pants_matches)

        matches = []

        if do_jacket_match:
            matches.append("Jacket")
        if do_pants_match:
            matches.append("Pants")

        if len(matches):
            print(f"""{' & '.join(matches)} matches for:
    Title: {item.get("title")}
    Price: {item.get("price", {}).get("amount")}€
    URL: {item.get("url")}

            """)


if __name__ == "__main__":
    asyncio.run(
        main()
    )
