import logging

from time import sleep

from _db import database
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


def delete_with(post_ids):
    for post_id in post_ids:
        logging.info("Deleting post: {0}".format(post_id))

        query = f"""SELECT tr.term_taxonomy_id, tt.taxonomy, t.name, t.term_id
FROM {CONFIG.TABLE_PREFIX}term_relationships tr, {CONFIG.TABLE_PREFIX}posts p, {CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t
WHERE p.ID={post_id} AND p.ID=tr.object_id AND tr.term_taxonomy_id=tt.term_taxonomy_id AND t.term_id=tt.term_id;
"""

        post_extra = database.select_with(query)

        post_extra_term_taxonomy_ids = [x[0] for x in post_extra]
        for term_taxonomy_id in post_extra_term_taxonomy_ids:
            database.delete_from(
                table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
                condition=f'term_taxonomy_id="{term_taxonomy_id}"',
            )

        post_extra_term_ids = [x[-1] for x in post_extra]

        for term_id in post_extra_term_ids:
            database.delete_from(
                table=f"{CONFIG.TABLE_PREFIX}termmeta",
                condition=f'term_id="{term_id}"',
            )

            database.delete_from(
                table=f"{CONFIG.TABLE_PREFIX}terms",
                condition=f'term_id="{term_id}"',
            )

        database.delete_from(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            condition=f'post_id="{post_id}"',
        )

        database.delete_from(
            table=f"{CONFIG.TABLE_PREFIX}term_relationships",
            condition=f'object_id="{post_id}"',
        )

        database.delete_from(
            table=f"{CONFIG.TABLE_PREFIX}posts",
            condition=f'ID="{post_id}"',
        )
        sleep(0.1)


def main():
    post_types = [
        "tvshows",
        "seasons",
        # "revision",
        "episodes",
        "movies",
        # "attachment",
        # "seasons",
    ]
    for post_type in post_types:
        post_ids = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts",
            condition=f'post_type="{post_type}"',
            cols="ID",
        )
        post_ids = [x[0] for x in post_ids]
        delete_with(post_ids)


def delete(postId):
    database.delete_from(table=f"{CONFIG.TABLE_PREFIX}posts", condition=f"ID={postId}")
    database.delete_from(
        table=f"{CONFIG.TABLE_PREFIX}postmeta", condition=f"post_id={postId}"
    )


def delete_with_title(title: str = "crossing lines"):
    cols = database.select_all_from(
        table=f"{CONFIG.TABLE_PREFIX}posts",
        condition=f"post_title LIKE '%{title}%'",
        cols="ID",
    )
    ids = [col[0] for col in cols]
    print(ids)
    delete_with(ids)


if __name__ == "__main__":
    # delete(131)
    main()
    # delete_with_title()
    # delete_with([753, 754])
