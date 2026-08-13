import { useState, useEffect } from 'react';
import { NavLink } from '@lark-apaas/client-toolkit-lite';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { DOC_NAV, type DocNavItem } from '@/data/doc';

interface DocSidebarProps {
  open: boolean;
  onClose: () => void;
}

function NavGroup({ item, level = 0 }: { item: DocNavItem; level?: number }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = item.children && item.children.length > 0;

  if (hasChildren) {
    return (
      <div className="space-y-0.5">
        <button
          onClick={() => setExpanded(!expanded)}
          className={cn(
            'flex w-full items-center justify-between rounded-md px-2 py-1.5 text-sm font-medium transition-colors',
            'text-foreground/80 hover:bg-accent hover:text-accent-foreground',
            level === 0 && 'font-semibold text-foreground',
          )}
          style={{ paddingLeft: `${level * 12 + 8}px` }}
        >
          <span>{item.title}</span>
          {expanded ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
        </button>
        {expanded && (
          <div className="space-y-0.5">
            {item.children!.map((child) => (
              <NavGroup key={child.id} item={child} level={level + 1} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <NavLink
      to={`#${item.id}`}
      className={({ isActive }) =>
        cn(
          'flex w-full items-center rounded-md px-2 py-1.5 text-sm transition-colors',
          isActive
            ? 'bg-primary/10 text-primary font-medium'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
        )
      }
      style={{ paddingLeft: `${level * 12 + 8}px` }}
    >
      {item.title}
    </NavLink>
  );
}

export default function DocSidebar({ open, onClose }: DocSidebarProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden transition-opacity duration-200',
          open ? 'opacity-100' : 'opacity-0 pointer-events-none',
        )}
        onClick={onClose}
      />

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-14 z-40 h-[calc(100vh-3.5rem)] w-64 shrink-0 border-r border-border/40 bg-background transition-transform duration-200',
          'md:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        )}
      >
        <ScrollArea className="h-full py-4 px-3">
          <div className="space-y-1">
            <div className="px-2 pb-2">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Aigility SDK
              </p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                v2.0.1
              </p>
            </div>
            {DOC_NAV.map((item) => (
              <NavGroup key={item.id} item={item} />
            ))}
          </div>
        </ScrollArea>
      </aside>
    </>
  );
}
