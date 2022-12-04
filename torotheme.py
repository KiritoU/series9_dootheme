import logging

from _db import database
from helper import helper
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class Torotheme:
    def __init__(self, film: dict, episodes: dict):
        self.film = film
        self.film["quality"] = (
            "HD"
            if "Quality" not in self.film["extra_info"].keys()
            else self.film["extra_info"]["Quality"]
        )
        self.episodes = episodes

    def insert_movie_details(self, post_id):
        if not self.episodes:
            return

        logging.info("Inserting movie players")

        episodes_keys = list(self.episodes.keys())
        episode_number = episodes_keys[0]
        episode = self.episodes[episode_number]

        len_episode_links = len(episode["links"])

        postmeta_data = [
            (post_id, "trgrabber_tlinks", len_episode_links),
        ]
        if (
            "Quality" in self.film["extra_info"].keys()
            and self.film["extra_info"]["Quality"]
        ):
            quality = self.film["extra_info"]["Quality"]
        else:
            quality = "HD"

        for i in range(len_episode_links):
            link = episode["links"][i]
            postmeta_data.append(
                (
                    post_id,
                    f"trglinks_{i}",
                    helper.generate_trglinks(i, link, quality=quality),
                )
            )

        helper.insert_postmeta(postmeta_data)

    def insert_root_film(self) -> list:
        condition_post_title = self.film["post_title"].replace("'", "''")
        condition = f"""post_title = '{condition_post_title}' AND post_type='{self.film["post_type"]}'"""
        be_post = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
        )
        if not be_post:
            logging.info(f'Inserting root film: {self.film["post_title"]}')
            post_data = helper.generate_film_data(
                self.film["post_title"],
                self.film["description"],
                self.film["post_type"],
                self.film["trailer_id"],
                self.film["fondo_player"],
                self.film["poster_url"],
                self.film["extra_info"],
            )

            return [helper.insert_film(post_data), True]
        else:
            return [be_post[0][0], False]

    def update_season_number_of_episodes(self, season_term_id, number_of_episodes):
        try:
            condition = f"term_id={season_term_id} AND meta_key='number_of_episodes'"
            be_number_of_episodes = database.select_all_from(
                table=f"{CONFIG.TABLE_PREFIX}termmeta",
                condition=condition,
                cols="meta_value",
            )[0][0]
            if int(be_number_of_episodes) < number_of_episodes:
                database.update_table(
                    table=f"{CONFIG.TABLE_PREFIX}termmeta",
                    set_cond=f"meta_value={number_of_episodes}",
                    where_cond=condition,
                )
        except Exception as e:
            helper.error_log(
                msg=f"Error while update_season_number_of_episodes\nSeason {season_term_id} - Number of episodes {number_of_episodes}\n{e}",
                log_file="torotheme.update_season_number_of_episodes.log",
            )

    def insert_episodes(self, post_id: int, season_term_id: int):
        episodes_keys = list(self.episodes.keys())
        episodes_keys.reverse()
        lenEpisodes = len(episodes_keys)

        self.update_season_number_of_episodes(season_term_id, lenEpisodes)

        for i in range(lenEpisodes):
            episode_number = episodes_keys[i]
            episode = self.episodes[episode_number]
            episode_title = episode["title"]
            len_episode_links = len(episode["links"])

            episode_term_name = (
                self.film["post_title"]
                + f' {self.film["season_number"]}x{episode_number}'
            )
            episode_term_id, isNewEpisode = helper.insert_terms(
                post_id=post_id, terms=[episode_term_name], taxonomy="episodes"
            )

            if not isNewEpisode:
                continue

            logging.info(f"Inserted new episode: {episode_title}")

            termmeta_data = [
                (episode_term_id, "episode_number", episode_number),
                (episode_term_id, "name", episode_title),
                (episode_term_id, "season_number", self.film["season_number"]),
                (episode_term_id, "tr_id_post", post_id),
                (episode_term_id, "still_path_hotlink", self.film["poster_url"]),
                (episode_term_id, "trgrabber_tlinks", len_episode_links),
            ]

            if (
                "Quality" in self.film["extra_info"].keys()
                and self.film["extra_info"]["Quality"]
            ):
                quality = self.film["extra_info"]["Quality"]
            else:
                quality = "HD"

            for i in range(len_episode_links):
                link = episode["links"][i]
                termmeta_data.append(
                    (
                        episode_term_id,
                        f"trglinks_{i}",
                        helper.generate_trglinks(i, link, quality=quality),
                    )
                )

            helper.insert_postmeta(termmeta_data, "termmeta")

    def insert_season(self, post_id: int):
        season_term_name = (
            self.film["post_title"] + " - Season " + self.film["season_number"]
        )
        season_term_id, isNewSeason = helper.insert_terms(
            post_id=post_id, terms=[season_term_name], taxonomy="seasons"
        )

        termmeta_data = [
            (season_term_id, "number_of_episodes", "0"),
            (season_term_id, "name", "Season " + self.film["season_number"]),
            (season_term_id, "overview", self.film["description"]),
            (season_term_id, "tr_id_post", post_id),
            (season_term_id, "season_number", self.film["season_number"]),
        ]

        if isNewSeason:
            logging.info(f"Inserted new season: {season_term_name}")
            helper.insert_postmeta(termmeta_data, "termmeta")

        return season_term_id

    def insert_film(self):
        (
            self.film["post_title"],
            self.film["season_number"],
        ) = helper.get_title_and_season_number(self.film["title"])

        if len(self.episodes) > 1:
            self.film["post_type"] = "series"

        post_id, isNewPostInserted = self.insert_root_film()

        if self.film["post_type"] != "series":
            if isNewPostInserted:
                self.insert_movie_details(post_id)
        else:
            season_term_id = self.insert_season(post_id)
            self.insert_episodes(post_id, season_term_id)
