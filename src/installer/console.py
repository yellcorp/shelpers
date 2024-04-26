SINGLE_LINE = "\u2500"
DOUBLE_LINE = "\u2550"
CORN = "\U0001f33d"

STEP_DIVIDER = DOUBLE_LINE * 60
OUTPUT_DIVIDER = SINGLE_LINE * len(STEP_DIVIDER)


def yes_or_no(prompt: str) -> bool:
    while True:
        response = input(prompt).lower()
        if response:
            if "yes".startswith(response):
                return True
            if "no".startswith(response):
                return False
        print("Enter y or n, or press Control-D to cancel")
