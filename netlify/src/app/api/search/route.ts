import { NextRequest, NextResponse } from 'next/server';
import { MongoClient } from 'mongodb';

let client: MongoClient | null = null;

async function getClient() {
  if (client) return client;
  const uri = process.env.MONGODB_URI as string;
  if (!uri) throw new Error('MONGODB_URI is not set');
  client = new MongoClient(uri, { serverSelectionTimeoutMS: 10000 });
  await client.connect();
  return client;
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const keyword = searchParams.get('keyword') || undefined;
    const docNumber = searchParams.get('docNumber') || undefined;
    const org = searchParams.get('org') || undefined;
    const party = searchParams.get('party') || undefined;
    const region = searchParams.get('region') || undefined;
    const caseType = searchParams.get('caseType') || undefined;
    const industry = searchParams.get('industry') || undefined;
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

    // Build MongoDB filter
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

    if (region) {
      filter['province'] = { $regex: region, $options: 'i' };
    }

    if (caseType) {
      filter['category'] = { $regex: caseType, $options: 'i' };
    }

    if (industry) {
      filter['industry'] = { $regex: industry, $options: 'i' };
    }

    if (dateFrom || dateTo) {
      // Assuming stored as ISO-like strings YYYY-MM-DD
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
      content: String(d['内容'] || d['content'] || ''),
      region: String(d['province'] || d['region'] || ''),
      caseType: String(d['category'] || ''),
      industry: String(d['industry'] || ''),
      legalBasis: String(d['law'] || ''),
      violationFacts: String(d['event'] || ''),
      legalProvisions: String(d['law'] || ''),
      penaltyDecision: String(d['penalty'] || ''),
      detailedContent: String(d['内容'] || d['content'] || ''),
      originalLink: String(d['链接'] || ''),
    }));

    return NextResponse.json({ data, total, page, pageSize });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || 'Search failed' }, { status: 500 });
  }
}