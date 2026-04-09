from concurrent.futures import ProcessPoolExecutor, as_completed
from scraper.z4ida import run_4zida
from scraper.halo_oglasi import run_halo_oglasi
from scraper.nekretnine_rs import run_nekretnine

def main():
    jobs = [("4zida", run_4zida,3),
            ("halo_oglasi",run_halo_oglasi,3),
            ("nekretnien",run_nekretnine,3)
            ]
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(function, max_pages):name
            for name,function,max_pages in jobs
            }
        for future in as_completed(futures):
            scraper_name = futures[future]
            try:
                result = future.result()
                print(f"[DONE] {scraper_name} zavrsen. Rezultat: {result}")
            except Exception as e:
                print(f"[ERROR] {scraper_name} pukao na :{e}")


if __name__ == "__main__":
    main()