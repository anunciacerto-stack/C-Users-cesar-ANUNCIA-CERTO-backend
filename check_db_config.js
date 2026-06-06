const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  const config = await prisma.botConfig.findFirst();
  console.log("Current Bot Config in Database:", JSON.stringify(config, null, 2));
}

main()
  .catch(e => console.error(e))
  .finally(() => prisma.$disconnect());
