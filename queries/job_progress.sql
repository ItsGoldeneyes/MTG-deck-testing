WITH last_finished AS (
    SELECT
        games.job_id,
        max(games.finished_on) AS finished_on
    FROM "public"."games" AS games
    WHERE games.finished_on IS NOT NULL
    GROUP BY games.job_id
),
job_created AS (
    SELECT
        games.job_id,
        min(games.created_on) AS created_on
    FROM "public"."games" AS games
    GROUP BY games.job_id
)
SELECT
    games.job_id,
    age(last_finished.finished_on, job_created.created_on) AS time_elapsed,
    count(games.primary_key) AS game_count,
    count(games.finished_on) AS games_evaluated,
    100.0 * count(games.finished_on) / nullif(count(games.primary_key), 0) AS percent_complete
FROM "public"."games" AS games
JOIN job_created ON games.job_id = job_created.job_id
LEFT JOIN last_finished ON games.job_id = last_finished.job_id
GROUP BY games.job_id, last_finished.finished_on, job_created.created_on
ORDER BY job_created.created_on DESC;
