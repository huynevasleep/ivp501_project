import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export const COLORS = {
  bg1: '#0a1424',
  bg2: '#10304a',
  accent: '#ffd34d',
  teal: '#35b5ae',
  text: '#f2f6fb',
  dim: '#9fb3c8',
  card: 'rgba(255,255,255,0.06)',
  border: 'rgba(255,255,255,0.14)',
};

export const FONT = '-apple-system, "Helvetica Neue", "Segoe UI", Roboto, sans-serif';

/** Nền chung + mờ dần ở 12 khung đầu/cuối của cảnh. */
export const Scene: React.FC<{children: React.ReactNode; duration: number}> = ({children, duration}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12, duration - 12, duration], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${COLORS.bg1} 0%, ${COLORS.bg2} 100%)`,
        fontFamily: FONT,
        color: COLORS.text,
        opacity,
      }}
    >
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(900px 500px at 85% 10%, rgba(53,181,174,.18), transparent), radial-gradient(700px 400px at 10% 95%, rgba(255,211,77,.10), transparent)',
        }}
      />
      <AbsoluteFill style={{padding: '70px 90px'}}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

export const Kicker: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div
    style={{
      fontSize: 30,
      letterSpacing: 6,
      textTransform: 'uppercase',
      color: COLORS.accent,
      fontWeight: 700,
      marginBottom: 14,
    }}
  >
    {children}
  </div>
);

export const H1: React.FC<{children: React.ReactNode; size?: number}> = ({children, size = 64}) => (
  <div style={{fontSize: size, fontWeight: 800, lineHeight: 1.15, marginBottom: 30}}>{children}</div>
);

/** Hiện dần từng phần tử con, mỗi phần tử trễ `step` khung. */
export const Stagger: React.FC<{
  items: React.ReactNode[];
  step?: number;
  from?: number;
  render: (item: React.ReactNode, i: number, style: React.CSSProperties) => React.ReactNode;
}> = ({items, step = 10, from = 0, render}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <>
      {items.map((item, i) => {
        const t = spring({frame: frame - from - i * step, fps, config: {damping: 200}});
        const style: React.CSSProperties = {
          opacity: t,
          transform: `translateY(${(1 - t) * 26}px)`,
        };
        return <React.Fragment key={i}>{render(item, i, style)}</React.Fragment>;
      })}
    </>
  );
};

export const Chip: React.FC<{children: React.ReactNode; color?: string}> = ({children, color = COLORS.teal}) => (
  <span
    style={{
      fontSize: 24,
      fontWeight: 700,
      color: '#07121f',
      background: color,
      borderRadius: 999,
      padding: '6px 18px',
      whiteSpace: 'nowrap',
    }}
  >
    {children}
  </span>
);

export const Card: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
  <div
    style={{
      background: COLORS.card,
      border: `1.5px solid ${COLORS.border}`,
      borderRadius: 22,
      padding: 32,
      ...style,
    }}
  >
    {children}
  </div>
);
