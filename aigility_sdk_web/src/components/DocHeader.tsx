import { Search, Menu, Github, BookOpen } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { DOC_NAV, type DocNavItem, type DocSearchResult } from '@/data/doc';
import { useNavigate } from 'react-router-dom';
import { UniversalLink } from '@lark-apaas/client-toolkit-lite';

interface DocHeaderProps {
  onToggleSidebar: () => void;
}

export default function DocHeader({ onToggleSidebar }: DocHeaderProps) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<DocSearchResult[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const q = query.toLowerCase();
    const found: DocSearchResult[] = [];

    // 从导航中搜索标题
    const searchNav = (items: DocNavItem[], parentTitle = '') => {
      for (const item of items) {
        const titleMatch = item.title.toLowerCase().includes(q);
        if (titleMatch) {
          found.push({
            id: item.id,
            title: item.title,
            section: parentTitle || '文档',
            snippet: `跳转到「${item.title}」章节`,
          });
        }
        if (item.children) {
          searchNav(item.children, item.title);
        }
      }
    };
    searchNav(DOC_NAV);

    setResults(found.slice(0, 10));
  }, [query]);

  const handleSelect = (id: string) => {
    setSearchOpen(false);
    setQuery('');
    navigate(`/#${id}`);
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 50);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md">
      <div className="flex h-14 items-center gap-4 px-4 md:px-6">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onToggleSidebar}
          aria-label="切换侧边栏"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <UniversalLink to="#top" className="flex items-center gap-2 font-semibold">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BookOpen className="h-4 w-4" />
          </div>
          <span className="hidden sm:inline text-foreground">
            Aigility SDK 文档
          </span>
        </UniversalLink>

        <div className="flex-1 flex justify-center max-w-md mx-auto">
          <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
            <DialogTrigger asChild>
              <button
                className="group flex w-full max-w-md items-center gap-2 rounded-md border border-input bg-background/50 px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                <Search className="h-4 w-4 shrink-0" />
                <span className="flex-1 text-left">搜索文档...</span>
                <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                  <span className="text-xs">⌘</span>K
                </kbd>
              </button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[520px] p-0">
              <DialogHeader className="px-4 pt-4 pb-2">
                <DialogTitle className="text-base font-medium">搜索文档</DialogTitle>
              </DialogHeader>
              <div className="px-4 pb-2">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    autoFocus
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="输入关键词搜索..."
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="max-h-[360px] overflow-y-auto px-2 pb-4">
                {query.trim() && results.length === 0 && (
                  <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                    未找到相关结果
                  </div>
                )}
                {!query.trim() && (
                  <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                    输入关键词开始搜索
                  </div>
                )}
                {results.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => handleSelect(r.id)}
                    className={cn(
                      'w-full flex flex-col gap-1 rounded-md px-3 py-2.5 text-left transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{r.title}</span>
                      <span className="text-xs text-muted-foreground">
                        {r.section}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground line-clamp-1">
                      {r.snippet}
                    </span>
                  </button>
                ))}
              </div>
            </DialogContent>
          </Dialog>
        </div>

        <div className="flex items-center gap-1">
          <span className="hidden md:inline text-xs text-muted-foreground mr-2">
            v2.0.1
          </span>
          <Button variant="ghost" size="icon" asChild aria-label="GitHub">
            <UniversalLink to="https://github.com/AIGility-Cloud-Innovation/aigility/tree/dev" target="_blank" rel="noreferrer">
              <Github className="h-4 w-4" />
            </UniversalLink>
          </Button>
        </div>
      </div>
    </header>
  );
}
