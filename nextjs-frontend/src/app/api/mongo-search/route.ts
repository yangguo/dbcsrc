import { NextRequest, NextResponse } from 'next/server';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
import { MongoClient } from 'mongodb';

declare global {
  // eslint-disable-next-line no-var
  var __mongoClient: MongoClient | undefined;
}

function getMongoUri(): string {
  const uri =
    process.env.MONGODB_URI ||
    process.env.MONGODB_URL ||
    process.env.MONGO_DB_URL ||
    '';
  return uri;
}

async function getClient() {
  if (global.__mongoClient) return global.__mongoClient;
  const uri = getMongoUri();
  if (!uri) throw new Error('MongoDB connection string not set (MONGODB_URI/MONGODB_URL/MONGO_DB_URL)');
  const client = new MongoClient(uri, { serverSelectionTimeoutMS: 10000 });
  await client.connect();
  global.__mongoClient = client;
  return client;
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const keyword = searchParams.get('keyword') || undefined;
    const docNumber = searchParams.get('docNumber') || undefined;
    const org = searchParams.get('org') || undefined;
    const party = searchParams.get('party') || undefined;
    const minAmountRaw = searchParams.get('minAmount');
    const minAmount = minAmountRaw ? Number(minAmountRaw) : undefined;
    const legalBasis = searchParams.get('legalBasis') || undefined;
    const dateFrom = searchParams.get('dateFrom') || undefined;
    const dateTo = searchParams.get('dateTo') || undefined;
    const page = Math.max(1, Number(searchParams.get('page') || '1'));
    const pageSize = Math.min(100, Math.max(1, Number(searchParams.get('pageSize') || '10')));

    const dbName = process.env.MONGODB_DB || 'pencsrc2';
    const collectionName = process.env.MONGODB_COLLECTION || 'csrc2analysis';

    const cli = await getClient();
    const col = cli.db(dbName).collection(collectionName);

    const filter: any = {};

    if (keyword) {
      filter.$or = [
        { '名称': { $regex: keyword, $options: 'i' } },
        { 'content': { $regex: keyword, $options: 'i' } },
        { '内容': { $regex: keyword, $options: 'i' } },
      ];
    }

    if (docNumber) {
      filter['文号'] = { $regex: docNumber, $options: 'i' };
    }

    if (org) {
      filter['机构'] = org;
    }

    if (party) {
      filter['people'] = { $regex: party, $options: 'i' };
    }

    if (legalBasis) {
      filter['law'] = { $regex: legalBasis, $options: 'i' };
    }

    if (dateFrom || dateTo) {
      filter['发文日期'] = {} as any;
      if (dateFrom) (filter['发文日期'] as any).$gte = dateFrom;
      if (dateTo) (filter['发文日期'] as any).$lte = dateTo;
    }

    const amountOr: any[] = [];
    if (typeof minAmount === 'number' && !Number.isNaN(minAmount)) {
      amountOr.push({ amount: { $gte: minAmount } });
      amountOr.push({ '罚款金额': { $gte: minAmount } });
    }

    const finalFilter = amountOr.length ? { $and: [filter, { $or: amountOr }] } : filter;

    const total = await col.countDocuments(finalFilter);
    const cursor = col
      .find(finalFilter, { projection: { _id: 0 } })
      .sort({ '发文日期': -1 })
      .skip((page - 1) * pageSize)
      .limit(pageSize);

    const docs = await cursor.toArray();

    const data = docs.map((d: any) => ({
      id: String(d['链接'] || d['id'] || ''),
      name: String(d['名称'] || d['title'] || ''),
      docNumber: String(d['文号'] || ''),
      date: String(d['发文日期'] || d['date'] || ''),
      org: String(d['机构'] || d['org'] || ''),
      party: String(d['people'] || ''),
      amount: Number(d['amount'] ?? d['罚款金额'] ?? 0) || 0,
      penalty: String(d['处罚类型'] || d['penalty'] || ''),
      violationFacts: String(d['event'] || ''),
      penaltyBasis: String(d['law'] || ''),
      penaltyDecision: String(d['penalty'] || ''),
      content: String(d['内容'] || d['content'] || ''),
      region: String(d['province'] || d['region'] || ''),
      industry: String(d['industry'] || ''),
      category: String(d['category'] || ''),
    }));

    return NextResponse.json({ data, total, page, pageSize });
  } catch (err: any) {
    console.error('mongo-search error:', err);
    return NextResponse.json({ error: err?.message || 'Search failed' }, { status: 500 });
  }
}
