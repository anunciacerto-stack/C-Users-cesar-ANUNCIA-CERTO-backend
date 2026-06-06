import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const trades = await prisma.botTrade.findMany({
    orderBy: { createdAt: 'desc' },
  });

  console.log('--- TRADES FOUND ---');
  console.log(JSON.stringify(trades, null, 2));
  console.log('--------------------');

  let totalBuy = 0;
  let totalSell = 0;
  let profitUsdt = 0;
  let buyTrades = 0;
  let sellTrades = 0;

  for (const trade of trades) {
    if (trade.type === 'COMPRA') {
      totalBuy += trade.value;
      buyTrades++;
    } else if (trade.type === 'VENDA') {
      totalSell += trade.value;
      sellTrades++;
      // Calculate profit using value diff if possible, or print profitPct
    }
  }

  console.log(`Total trades: ${trades.length} (COMPRA: ${buyTrades}, VENDA: ${sellTrades})`);
  console.log(`Total Buy Value: $${totalBuy.toFixed(2)} USDT`);
  console.log(`Total Sell Value: $${totalSell.toFixed(2)} USDT`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
