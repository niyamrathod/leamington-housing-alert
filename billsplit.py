"""
billsplit.py

A small standalone calculator for splitting a total rent/bills figure
between housemates in proportion to their room size. It doesn't touch
the scraper/alert system at all, and doesn't save anything - just run
it, answer the prompts, and get each person's share.

Run with:
    python billsplit.py
"""


def _prompt_float(prompt_text):
    """Keep asking until the user enters a valid number greater than 0."""
    while True:
        raw_value = input(prompt_text).strip()
        try:
            value = float(raw_value)
        except ValueError:
            print("  Please enter a number (e.g. 650 or 120.5).")
            continue
        if value <= 0:
            print("  Please enter a number greater than 0.")
            continue
        return value


def collect_housemates():
    """
    Ask for each housemate's name and room size, one at a time, until a
    blank name is entered. Room size can be an exact measurement (sq ft)
    or just a relative ranking number (e.g. 1-5 for "smallest to
    biggest") - the maths works the same either way, since every share
    is purely proportional to the numbers entered.
    """
    housemates = []
    print("Enter each housemate's name and room size. Leave the name blank when done.\n")
    while True:
        name = input(f"Housemate {len(housemates) + 1} name (blank to finish): ").strip()
        if not name:
            break
        room_size = _prompt_float(f"  {name}'s room size (sq ft, or a relative ranking number): ")
        housemates.append({"name": name, "room_size": room_size})
    return housemates


def split_by_room_size(total, housemates):
    """
    Split `total` between housemates in proportion to room_size.

    Every share is rounded to the nearest penny except the last
    person's, which gets whatever is left over after the others are
    rounded. Rounding each share independently can leave the total a
    few pence off from what was actually entered (e.g. three shares of
    £33.33 only add up to £99.99, not £100) - giving the remainder to
    the last person keeps the total exactly right.
    """
    total_room_size = sum(housemate["room_size"] for housemate in housemates)
    shares = []
    running_total = 0.0

    for housemate in housemates[:-1]:
        share = round(total * housemate["room_size"] / total_room_size, 2)
        shares.append({"name": housemate["name"], "share": share})
        running_total += share

    last_housemate = housemates[-1]
    shares.append({"name": last_housemate["name"], "share": round(total - running_total, 2)})

    return shares


if __name__ == "__main__":
    print("=== Leamington Housing bill/rent split calculator ===\n")

    total = _prompt_float("Total amount to split (£): ")
    housemates = collect_housemates()

    if len(housemates) < 2:
        print("\nNeed at least 2 housemates to split anything - exiting.")
    else:
        shares = split_by_room_size(total, housemates)
        print(f"\nSplit of £{total:.2f} by room size:\n")
        for entry in shares:
            print(f"  {entry['name']}: £{entry['share']:.2f}")
        print(f"\n  Total: £{sum(entry['share'] for entry in shares):.2f}")
