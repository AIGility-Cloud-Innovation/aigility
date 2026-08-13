import { useState, useEffect } from 'react';
import DocHeader from '@/components/DocHeader';
import DocSidebar from '@/components/DocSidebar';
import DocContent from '@/components/DocContent';
import { DOC_CONTENT } from '@/data/doc';
import { useIsMobile } from '@/hooks/use-mobile';
import { UniversalLink } from '@lark-apaas/client-toolkit-lite';

export default function HomePage() {
  const isMobile = useIsMobile();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isMobile) {
      setSidebarOpen(false);
    }
  }, [isMobile]);

  // Smooth scroll for anchor links
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLAnchorElement;
      const href = target.closest('a[href^="#"]')?.getAttribute('href');
      if (href && href.startsWith('#')) {
        e.preventDefault();
        const id = href.slice(1);
        const el = document.getElementById(id);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          history.pushState(null, '', href);
        }
      }
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  return (
    <div id="top" className="min-h-screen bg-background text-foreground">
      <DocHeader onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
      <DocSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="md:pl-64 pt-2">
        <div className="mx-auto max-w-4xl px-4 py-8 md:px-8 md:py-10">
          {/* Breadcrumb */}
          <nav className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
            <UniversalLink to="#top" className="hover:text-foreground transition-colors">
              Aigility SDK
            </UniversalLink>
            <span className="text-muted-foreground/50">/</span>
            <span className="text-foreground">文档</span>
          </nav>

          <DocContent content={DOC_CONTENT} />

          {/* Footer */}
          <footer className="mt-16 pt-8 border-t border-border/40 text-sm text-muted-foreground">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <p>Aigility SDK (ADK) v2.0.1</p>
                <p className="text-xs mt-1">
                  由 AIGility Cloud Innovation 维护
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <UniversalLink to="#top" className="hover:text-foreground transition-colors">
                  返回顶部
                </UniversalLink>
                <UniversalLink
                  to="https://github.com"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  GitHub
                </UniversalLink>
              </div>
            </div>
          </footer>
        </div>
      </main>
    </div>
  );
}
