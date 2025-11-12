import { source } from '@/lib/source';
import { createI18nSearchAPI } from 'fumadocs-core/search/server';

export const { GET } = createI18nSearchAPI('advanced', {
  indexes: source.getPages().map((page) => ({
    title: page.data.title,
    description: page.data.description,
    structuredData: page.data.structuredData,
    id: page.url,
    url: page.url,
    locale: page.locale,
  })),
});
