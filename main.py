import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

from scraper.halo_oglasi import run_halo_oglasi
from scraper.z4ida import run_4zida
from scraper.nekretnine_rs import run_nekretnine


def run_full():
    """
    Prolazi kroz sve stranice i skuplja sve oglase.
    Koristi se samo prvi put ili kad želiš da napuniš bazu ispočetka.
    """
    print("[MAIN] Pokrećem FULL SCRAPE...")
    jobs = [
        ("halo_oglasi", run_halo_oglasi, None),
        ("4zida",       run_4zida,       None),
        ("nekretnine",  run_nekretnine,  None),
    ]
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(function, max_pages): name
            for name, function, max_pages in jobs
        }
        for future in as_completed(futures):
            scraper_name = futures[future]
            try:
                future.result()
                print(f"[DONE] {scraper_name} zavrsen.")
            except Exception as e:
                print(f"[ERROR] {scraper_name} pukao: {e}")


def run_daily():
    """
    Svaki dan skuplja samo nove oglase.
    Staje čim pronađe oglas koji već postoji u bazi.
    Brzo završava — obično par minuta.
    """
    print("[MAIN] Pokrećem DAILY UPDATE...")

    # Sekvencijalno — jedan po jedan da se ne bi opteretio server
    # EC2 t3.micro ima 1GB RAM, 3 browsera paralelno može biti previše
    run_halo_oglasi(mode="daily")
    run_4zida(mode="daily")
    run_nekretnine(mode="daily")

    print("[MAIN] DAILY UPDATE završen.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["full", "daily"],
        default="daily",
        help="full = sve stranice, daily = samo novi oglasi (default)"
    )
    args = parser.parse_args()

    if args.mode == "full":
        run_full()
    else:
        run_daily()


if __name__ == "__main__":
    main()