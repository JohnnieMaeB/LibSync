
import { Pinecone } from '@pinecone-database/pinecone';

const pc = new Pinecone({
  apiKey: process.env.PINECONE_API_KEY || 'PINECONE_API_KEY'
});

const indexName = 'libsync-policy-index';

async function checkAndCreateIndex() {
  try {
    const existingIndexes = await pc.listIndexes();
    const indexExists = existingIndexes.indexes.some(index => index.name === indexName);

    if (indexExists) {
      console.log(`Index '${indexName}' already exists.`);
      return;
    }

    console.log(`Index '${indexName}' does not exist. Creating...`);
    await pc.createIndexForModel({
      name: indexName,
      cloud: 'aws',
      region: 'us-east-1',
      embed: {
        model: 'llama-text-embed-v2',
        fieldMap: { text: 'chunk_text' },
      },
      waitUntilReady: true,
    });
    console.log(`Index '${indexName}' created successfully.`);
  } catch (error) {
    console.error('An error occurred:', error);
    process.exit(1);
  }
}

checkAndCreateIndex();
