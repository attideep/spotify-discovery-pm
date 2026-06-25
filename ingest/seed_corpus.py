"""Seed corpus for demo mode when live scraping unavailable."""

from __future__ import annotations

from datetime import datetime, timezone

from ingest.normalize import normalize, save_corpus

SEED_TEXTS = [
    ("play_store", "android", 2, "Discover Weekly used to be great but now it's the same vibe every week. I just replay my 2019 playlists because at least I know what I'm getting."),
    ("play_store", "android", 3, "Recommendations feel like they're optimizing for what I already listen to. I want to find NEW artists not more of the same indie folk."),
    ("app_store", "ios", 2, "I pay for Premium but still listen to the same 3 playlists on commute. Discovery feels like work — scrolling through bad suggestions."),
    ("app_store", "ios", 4, "Love the app but Daily Mix and Discover Weekly overlap so much. Why can't it explain why it's suggesting something?"),
    ("reddit_truespotify", "reddit", None, "Does anyone else feel stuck in a loop? My Release Radar is 80% artists I already follow and Discover Weekly hasn't surprised me in months."),
    ("reddit_truespotify", "reddit", None, "The algorithm pigeonholed me into lo-fi hip hop. Every 'Discover' playlist sounds identical. I miss when friends would send me random songs."),
    ("reddit_spotify", "reddit", None, "Autoplay keeps playing the same artists from my liked songs. I tried Radio but it just cycles familiar tracks. How do you actually find new music?"),
    ("reddit_spotifyplaylists", "reddit", None, "I built comfort playlists for every mood and haven't explored in 2 years. Spotify keeps reinforcing my bubble with 'Made For You' that never pushes boundaries."),
    ("hackernews", "forum", None, "Spotify's collaborative filtering is great at retention, terrible at genuine discovery. The jump from familiar to novel is too abrupt — one weird track and I skip."),
    ("hackernews", "forum", None, "I wish recommendations came with context: 'because you liked X's groove but wanted more energy.' Instead it's a black box shuffle."),
    ("play_store", "android", 1, "Shuffle plays the same 50 songs despite having 2000 liked songs. Discovery tab is full of podcasts I don't want."),
    ("app_store", "ios", 3, "Spotify knows my taste too well — I never hear anything outside my comfort zone unless a friend shares a link."),
    ("reddit_truespotify", "reddit", None, "Time poverty is real. I don't have 30 minutes to curate. I want low-effort discovery during my 20-minute commute that's NOT my gym playlist again."),
    ("reddit_spotify", "reddit", None, "Algorithm anxiety: I skip anything that sounds 'recommended' because past suggestions were so off. I stick to albums I know."),
    ("play_store", "android", 4, "Social discovery died. I used to see what friends listened to. Now it's all algorithmic feeds that feel sterile."),
    ("app_store", "ios", 2, "Genre explorer burnout — tried Discover Weekly for a year, saved maybe 5 songs. Same-sounding tracks every Monday."),
    ("hackernews", "forum", None, "The cognitive cost of evaluating new music is high. Repeating playlists is rational when discovery ROI is low."),
    ("reddit_spotifyplaylists", "reddit", None, "Context switching kills discovery. Work focus, gym energy, chill evening — I have a playlist for each and never deviate."),
    ("play_store", "android", 3, "Blend and friend activity helped me find music. Algorithm alone doesn't trust my mood — I need a bridge from safe to new."),
    ("app_store", "ios", 5, "When Spotify gets it right with a fresh artist it's magical. But that's rare. Usually I retreat to old favorites."),
    ("reddit_truespotify", "reddit", None, "Premium user 5+ years. 70% listening from Liked Songs. Discovery score 2/10. I want gradual novelty not random jumps."),
    ("hackernews", "forum", None, "Batch playlists like Discover Weekly aren't moment-aware. I need something that reads 'focus work Tuesday morning' not 'here's 30 songs Monday'."),
    ("play_store", "android", 2, "Podcast recommendations took over my home feed. Hard to even find the music discovery features anymore."),
    ("app_store", "ios", 3, "Why does Radio play the same 15 tracks? There's a whole catalog but it feels like a loop."),
    ("reddit_spotify", "reddit", None, "I distrust the algorithm after it pushed the same artist 50 times because of one accidental play. Now I manually pick everything."),
    ("reddit_truespotify", "reddit", None, "Comfort loop curator here — updating playlists feels like a chore. Discovery needs to meet me where I am, not demand I browse."),
    ("play_store", "android", 4, "Smart Shuffle still feels like the same pool. Would pay extra for an AI DJ that explains each pick."),
    ("hackernews", "forum", None, "Explainability would increase save rate. Tell me WHY this track bridges from Khruangbin to something new."),
    ("app_store", "ios", 2, "Same artists on Release Radar every week. New music discovery is broken for long-term users."),
    ("reddit_spotifyplaylists", "reddit", None, "Friend sent me a song last month — best discovery experience I've had all year. Algorithm can't replicate that trust."),
]


def build_seed_corpus(path: str = "data/corpus.json") -> str:
    records = []
    for i, (source, platform, rating, text) in enumerate(SEED_TEXTS):
        records.append(
            normalize(
                source,
                platform,
                text,
                rating=float(rating) if rating else None,
                date=datetime.now(timezone.utc),
                url=f"https://example.com/seed/{i}",
                idx=i,
            )
        )
    # Expand with variations to reach ~120 seed records
    extras = []
    templates = [
        "I keep replaying {playlist} because discovery on Spotify feels overwhelming.",
        "Recommendations don't match my {context} — same artists every time.",
        "Want music like {artist} but bolder. Discover Weekly never delivers.",
        "Stuck in comfort loop since {year}. Algorithm won't push me out.",
        "Skip rate on Discover Weekly is 90%. Only trust my saved {genre} playlists.",
    ]
    playlists = ["Work Focus", "Gym Bangers", "Chill Vibes", "Road Trip", "Sleep"]
    contexts = ["morning commute", "late night coding", "weekend cooking", "running"]
    artists = ["Tame Impala", "Bon Iver", "Daft Punk", "Khruangbin", "Radiohead"]
    years = ["2020", "2021", "2022", "2023"]
    genres = ["indie", "electronic", "hip-hop", "jazz", "rock"]
    idx = len(records)
    for ti, tmpl in enumerate(templates):
        for j in range(18):
            text = tmpl.format(
                playlist=playlists[(ti + j) % 5],
                context=contexts[(ti + j) % 4],
                artist=artists[(ti + j) % 5],
                year=years[(ti + j) % 4],
                genre=genres[(ti + j) % 5],
            )
            src = ["play_store", "app_store", "reddit_truespotify", "reddit_spotify"][j % 4]
            plat = ["android", "ios", "reddit", "reddit"][j % 4]
            extras.append(
                normalize(src, plat, text, rating=2.0 + (j % 3), idx=idx)
            )
            idx += 1
    records.extend(extras)
    return str(save_corpus(records, path))


if __name__ == "__main__":
    p = build_seed_corpus()
    print(f"Seed corpus: {p}")
