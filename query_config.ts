import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const configs = await prisma.botConfig.findMany();
  console.log('--- BOT CONFIGS IN DATABASE ---');
  console.log(JSON.stringify(configs, null, 2));
  console.log('-------------------------------');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
