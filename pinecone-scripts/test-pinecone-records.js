
import { Pinecone } from '@pinecone-database/pinecone';

const pc = new Pinecone({
  apiKey: process.env.PINECONE_API_KEY || 'PINECONE_API_KEY'
});

const indexName = 'libsync-policy-index';
const query = 'Famous historical structures and monuments';

async function testIndex() {
  try {
    const index = pc.index(indexName).namespace("ns1");
    console.log(`Querying index '${indexName}' with query: '${query}'`);

    const rerankedResults = await index.searchRecords({
      query: {
        topK: 5,
        inputs: { text: query },
      },
      rerank: {
        model: 'bge-reranker-v2-m3',
        topN: 5,
        rankFields: ['chunk_text'],
      },
    });

    console.log('Reranked query results:', rerankedResults);

    const stats = await index.describeIndexStats();
    console.log('Index stats:', stats);

  } catch (error) {
    console.error('An error occurred during the test:', error);
    process.exit(1);
  }
}

testIndex();
