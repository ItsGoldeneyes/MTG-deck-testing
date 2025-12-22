WITH deck_results AS (
    SELECT deck_version_id1 AS  deck_version_id, deck1_wins AS wins
    FROM public.games
    WHERE job_id = 'e01a9791-a042-4257-a570-1a24965305d9'

    UNION ALL

    SELECT deck_version_id2 AS  deck_version_id, deck2_wins AS wins
    FROM public.games
    WHERE job_id = 'e01a9791-a042-4257-a570-1a24965305d9'

    UNION ALL

    SELECT deck_version_id3 AS  deck_version_id, deck3_wins AS wins
    FROM public.games
    WHERE job_id = 'e01a9791-a042-4257-a570-1a24965305d9'

    UNION ALL

    SELECT deck_version_id4 AS  deck_version_id, deck4_wins AS wins
    FROM public.games
    WHERE job_id = 'e01a9791-a042-4257-a570-1a24965305d9'
)

SELECT
     deck_results.deck_version_id,
     deck_name,
    COUNT(*) AS games_played,
    SUM(wins) AS total_wins,
    ROUND(SUM(wins)::numeric / COUNT(*) , 3) AS avg_winrate_per_game
FROM deck_results
LEFT JOIN decks
ON deck_results. deck_version_id = decks.deck_version_id
GROUP BY  1,2
ORDER BY avg_winrate_per_game DESC;