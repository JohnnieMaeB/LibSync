
import { Pinecone } from '@pinecone-database/pinecone';

const pc = new Pinecone({
  apiKey: process.env.PINECONE_API_KEY || 'PINECONE_API_KEY'
});

const indexName = 'libsync-policy-index';

const records = [
    { "_id": "rec1", "chunk_text": "The Eiffel Tower was completed in 1889 and stands in Paris, France.", "category": "history" },
    { "_id": "rec2", "chunk_text": "Photosynthesis allows plants to convert sunlight into energy.", "category": "science" },
    { "_id": "rec3", "chunk_text": "Albert Einstein developed the theory of relativity.", "category": "science" },
    { "_id": "rec4", "chunk_text": "The mitochondrion is often called the powerhouse of the cell.", "category": "biology" },
    { "_id": "rec5", "chunk_text": "Shakespeare wrote many famous plays, including Hamlet and Macbeth.", "category": "literature" },
    { "_id": "rec6", "chunk_text": "Water boils at 100°C under standard atmospheric pressure.", "category": "physics" },
    { "_id": "rec7", "chunk_text": "The Great Wall of China was built to protect against invasions.", "category": "history" },
    { "_id": "rec8", "chunk_text": "Honey never spoils due to its low moisture content and acidity.", "category": "food science" },
    { "_id": "rec9", "chunk_text": "The speed of light in a vacuum is approximately 299,792 km/s.", "category": "physics" },
    { "_id": "rec10", "chunk_text": "Newton's laws describe the motion of objects.", "category": "physics" }
];

async function upsertRecords() {
  try {
    const index = pc.index(indexName).namespace("ns1");
    const recordIds = records.map(record => record._id);
    const fetchResponse = await index.fetch(recordIds);

    const existingIds = Object.keys(fetchResponse.records);
    const recordsToUpsert = records.filter(record => !existingIds.includes(record._id));

    if (recordsToUpsert.length > 0) {
      console.log(`Upserting ${recordsToUpsert.length} new records into index '${indexName}'...`);
      await index.upsertRecords(recordsToUpsert);
      console.log('Records upserted successfully.');
    } else {
      console.log('All records already exist in the index. No upsert needed.');
    }
  } catch (error) {
    console.error('An error occurred during the upsert process:', error);
    process.exit(1);
  }
}

upsertRecords();
