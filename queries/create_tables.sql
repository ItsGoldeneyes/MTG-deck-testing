CREATE TABLE IF NOT EXISTS "public"."decks" (
  "primary_key" UUID NOT NULL,
  "card_name" TEXT NULL,
  "deck_name" TEXT NULL,
  "set_code" TEXT NULL,
  "quantity" INTEGER NULL,
  "uploaded_on" TIMESTAMP NULL,
  "tag" TEXT NULL,
  "colour" TEXT NULL,
  "format" TEXT NULL,
  "category" TEXT NULL,
  CONSTRAINT "PK_decks" PRIMARY KEY ("primary_key")
);

CREATE TABLE "public"."games" (
  "primary_key" UUID NOT NULL,
  "deck1_name" TEXT NULL,
  "deck2_name" TEXT NULL,
  "deck3_name" TEXT NULL,
  "deck4_name" TEXT NULL,
  "job_id" UUID NULL,
  "game_count" INTEGER NULL,
  "deck1_wins" INTEGER NULL,
  "deck2_wins" INTEGER NULL,
  "deck3_wins" INTEGER NULL,
  "deck4_wins" INTEGER NULL,
  "turn_counts" JSON NULL,
  "device_id" UUID NULL,
  "format" TEXT NULL,
  "created_on" TIMESTAMP NULL,
  "finished_on" TIMESTAMP NULL,
  CONSTRAINT "PK_games" PRIMARY KEY ("primary_key")
);
