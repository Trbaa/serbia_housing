import random

DESKTOP_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",

    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",

    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
    "Gecko/20100101 Firefox/124.0",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",

    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) "
    "Gecko/20100101 Firefox/126.0",

    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",

    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Safari/605.1.15",
]

ANDROID_USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",

    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",

    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",

    "Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",

    "Mozilla/5.0 (Linux; Android 14; moto g84 5G) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",

    "Mozilla/5.0 (Android 14; Mobile; rv:125.0) "
    "Gecko/125.0 Firefox/125.0",

    "Mozilla/5.0 (Android 13; Mobile; rv:124.0) "
    "Gecko/124.0 Firefox/124.0",
]

APPLE_MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
    "Mobile/15E148 Safari/604.1",

    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 "
    "Mobile/15E148 Safari/604.1",

    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
    "Mobile/15E148 Safari/604.1",
]


def get_browser_profile():
    device_type = random.choices(
        population=["desktop", "android", "apple_mobile"],
        weights=[80, 15, 5],
        k=1
    )[0]

    if device_type == "desktop":
        return {
            "user_agent": random.choice(DESKTOP_USER_AGENTS),
            "viewport": random.choice([
                {"width": 1366, "height": 768},
                {"width": 1440, "height": 900},
                {"width": 1536, "height": 864},
                {"width": 1920, "height": 1080},
            ]),
            "is_mobile": False,
            "has_touch": False,
            "device_scale_factor": 1,
        }

    if device_type == "android":
        return {
            "user_agent": random.choice(ANDROID_USER_AGENTS),
            "viewport": random.choice([
                {"width": 360, "height": 800},
                {"width": 393, "height": 851},
                {"width": 412, "height": 915},
            ]),
            "is_mobile": True,
            "has_touch": True,
            "device_scale_factor": random.choice([2, 2.5, 3]),
        }

    return {
        "user_agent": random.choice(APPLE_MOBILE_USER_AGENTS),
        "viewport": random.choice([
            {"width": 375, "height": 812},
            {"width": 390, "height": 844},
            {"width": 430, "height": 932},
            {"width": 820, "height": 1180},
        ]),
        "is_mobile": True,
        "has_touch": True,
        "device_scale_factor": random.choice([2, 3]),
    }