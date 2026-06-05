CREATE EXTENSION IF NOT EXISTS "pgcrypto";

ALTER TABLE "Classified" DROP CONSTRAINT IF EXISTS "Classified_userId_fkey";
ALTER TABLE "MuralPost" DROP CONSTRAINT IF EXISTS "MuralPost_userId_fkey";
ALTER TABLE "Donation" DROP CONSTRAINT IF EXISTS "Donation_userId_fkey";

ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "newId" UUID DEFAULT gen_random_uuid();
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "role" TEXT NOT NULL DEFAULT 'user';
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'User' AND column_name = 'created_at'
  ) THEN
    EXECUTE 'ALTER TABLE "User" RENAME COLUMN "created_at" TO "createdAt"';
  END IF;
END $$;

ALTER TABLE "Classified" ADD COLUMN IF NOT EXISTS "userId_new" UUID;
ALTER TABLE "MuralPost" ADD COLUMN IF NOT EXISTS "userId_new" UUID;
ALTER TABLE "Donation" ADD COLUMN IF NOT EXISTS "userId_new" UUID;

UPDATE "Classified" c
SET "userId_new" = u."newId"
FROM "User" u
WHERE c."userId" = u."id";

UPDATE "MuralPost" m
SET "userId_new" = u."newId"
FROM "User" u
WHERE m."userId" = u."id";

UPDATE "Donation" d
SET "userId_new" = u."newId"
FROM "User" u
WHERE d."userId" = u."id";

ALTER TABLE "User" DROP CONSTRAINT IF EXISTS "User_pkey";
ALTER TABLE "User" DROP COLUMN IF EXISTS "id";
ALTER TABLE "User" RENAME COLUMN "newId" TO "id";
ALTER TABLE "User" ADD CONSTRAINT "User_pkey" PRIMARY KEY ("id");

ALTER TABLE "Classified" DROP COLUMN IF EXISTS "userId";
ALTER TABLE "MuralPost" DROP COLUMN IF EXISTS "userId";
ALTER TABLE "Donation" DROP COLUMN IF EXISTS "userId";

ALTER TABLE "Classified" RENAME COLUMN "userId_new" TO "userId";
ALTER TABLE "MuralPost" RENAME COLUMN "userId_new" TO "userId";
ALTER TABLE "Donation" RENAME COLUMN "userId_new" TO "userId";

DROP INDEX IF EXISTS "Classified_userId_idx";
DROP INDEX IF EXISTS "MuralPost_userId_idx";
DROP INDEX IF EXISTS "Donation_userId_idx";

CREATE INDEX "Classified_userId_idx" ON "Classified"("userId");
CREATE INDEX "MuralPost_userId_idx" ON "MuralPost"("userId");
CREATE INDEX "Donation_userId_idx" ON "Donation"("userId");

ALTER TABLE "Classified" ADD CONSTRAINT "Classified_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "MuralPost" ADD CONSTRAINT "MuralPost_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "Donation" ADD CONSTRAINT "Donation_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
