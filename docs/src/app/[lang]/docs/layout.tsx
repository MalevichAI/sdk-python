import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { baseOptions } from '@/lib/layout.shared';
import { notFound } from 'next/navigation';

export default async function Layout({
  params,
  children,
}: LayoutProps<'/[lang]/docs'>) {
  const lang = (await params).lang;
  const tree = source.pageTree[lang];

  if (!tree) {
    notFound();
  }

  return (
    <DocsLayout tree={tree} {...baseOptions(lang)}>
      {children}
    </DocsLayout>
  );
}
