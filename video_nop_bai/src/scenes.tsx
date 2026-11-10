import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Card, Chip, COLORS, H1, Kicker, Scene, Stagger} from './ui';
import {ALGOS, COURSE, DATE, DEMO_CAPTIONS, END2END, GOALS, HONEST, PIPELINE, REPO, RESULTS, TEAM, TITLE, TOPIC} from './data';

// ---------- 1. Tiêu đề ----------
export const TitleScene: React.FC<{duration: number}> = ({duration}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: frame - 6, fps, config: {damping: 200}});
  const ballX = interpolate(frame, [0, duration], [-100, 2020]);
  const ballY = 880 - Math.abs(Math.sin(frame / 11)) * 150;
  return (
    <Scene duration={duration}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', textAlign: 'center'}}>
        <div style={{opacity: pop, transform: `scale(${0.9 + pop * 0.1})`, maxWidth: 1500}}>
          <Kicker>{COURSE}</Kicker>
          <div style={{fontSize: 40, color: COLORS.dim, fontWeight: 700, marginBottom: 20}}>{TOPIC}</div>
          <H1 size={88}>{TITLE}</H1>
          <div style={{fontSize: 34, color: COLORS.dim}}>{DATE}</div>
        </div>
      </AbsoluteFill>
      {/* quả bóng nảy ngang màn hình */}
      <div
        style={{
          position: 'absolute',
          left: ballX,
          top: ballY,
          width: 46,
          height: 46,
          borderRadius: '50%',
          background: COLORS.accent,
          boxShadow: '0 0 40px rgba(255,211,77,.8)',
        }}
      />
    </Scene>
  );
};

// ---------- 2. Nhóm ----------
export const TeamScene: React.FC<{duration: number}> = ({duration}) => (
  <Scene duration={duration}>
    <Kicker>Nhóm thực hiện</Kicker>
    <H1>4 thành viên</H1>
    <div style={{display: 'flex', gap: 36, marginTop: 30}}>
      <Stagger
        items={TEAM.map((m) => m.name)}
        step={12}
        from={10}
        render={(_, i, style) => (
          <Card style={{...style, flex: 1, textAlign: 'center', padding: '48px 26px'}}>
            <div
              style={{
                width: 150,
                height: 150,
                borderRadius: '50%',
                margin: '0 auto 28px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 60,
                fontWeight: 800,
                color: '#07121f',
                background: i % 2 ? COLORS.teal : COLORS.accent,
              }}
            >
              {TEAM[i].name.split(' ').slice(-1)[0].slice(0, 2).toUpperCase()}
            </div>
            <div style={{fontSize: 38, fontWeight: 800, marginBottom: 10}}>{TEAM[i].name}</div>
            <div style={{fontSize: 26, color: COLORS.accent, marginBottom: 16}}>{TEAM[i].id}</div>
            <div style={{fontSize: 26, color: COLORS.dim, lineHeight: 1.4}}>{TEAM[i].role}</div>
          </Card>
        )}
      />
    </div>
  </Scene>
);

// ---------- 3. Mục tiêu ----------
export const GoalsScene: React.FC<{duration: number}> = ({duration}) => (
  <Scene duration={duration}>
    <Kicker>Bài toán</Kicker>
    <H1>Ba mục tiêu của đề tài</H1>
    <div style={{display: 'flex', flexDirection: 'column', gap: 34, marginTop: 24, maxWidth: 1560}}>
      <Stagger
        items={GOALS}
        step={22}
        from={12}
        render={(item, i, style) => (
          <Card style={{...style, display: 'flex', alignItems: 'center', gap: 34}}>
            <div
              style={{
                minWidth: 76,
                height: 76,
                borderRadius: 20,
                background: COLORS.accent,
                color: '#07121f',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 42,
                fontWeight: 800,
              }}
            >
              {i + 1}
            </div>
            <div style={{fontSize: 36, lineHeight: 1.4}}>{item}</div>
          </Card>
        )}
      />
    </div>
  </Scene>
);

// ---------- 4. Pipeline: mỗi bước hiện đúng tấm ảnh của bước đó ----------
export const PipelineScene: React.FC<{duration: number}> = ({duration}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const from = 14;
  const stepGap = Math.floor((duration - 120) / PIPELINE.length);
  const active = Math.max(0, Math.min(PIPELINE.length - 1, Math.floor((frame - from) / stepGap)));
  const pop = spring({frame: (frame - from) % stepGap, fps, config: {damping: 200}});
  return (
    <Scene duration={duration}>
      <Kicker>Mục tiêu 1 + 2 · chạy trên video 11 phút ({END2END.url})</Kicker>
      <H1 size={56}>Từng bước chọn timecode highlight — có ảnh từng bước</H1>
      <div style={{display: 'flex', gap: 46}}>
        <div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: 14}}>
          <Stagger
            items={PIPELINE.map((p) => p.step)}
            step={stepGap}
            from={from}
            render={(_, i, style) => (
              <div
                style={{
                  ...style,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 18,
                  padding: '6px 12px',
                  borderRadius: 14,
                  background: i === active ? 'rgba(53,181,174,.16)' : 'transparent',
                  border: `1.5px solid ${i === active ? COLORS.teal : 'transparent'}`,
                }}
              >
                <div
                  style={{
                    minWidth: 42,
                    height: 42,
                    borderRadius: '50%',
                    background: i === active ? COLORS.accent : COLORS.teal,
                    color: '#07121f',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 800,
                    fontSize: 24,
                  }}
                >
                  {i + 1}
                </div>
                <div style={{fontSize: 26, flex: 1, lineHeight: 1.3}}>{PIPELINE[i].step}</div>
                <Chip color={i % 2 ? COLORS.accent : COLORS.teal}>{PIPELINE[i].algo}</Chip>
              </div>
            )}
          />
        </div>
        <Card style={{flex: 1, alignSelf: 'stretch', padding: 22, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
          <div key={active} style={{opacity: pop, transform: `scale(${0.96 + pop * 0.04})`, textAlign: 'center'}}>
            <Img
              src={staticFile(PIPELINE[active].img)}
              style={{width: '100%', height: 540, objectFit: 'contain', borderRadius: 12, background: '#06101d'}}
            />
            <div style={{fontSize: 25, color: COLORS.text, marginTop: 18}}>
              <span style={{color: COLORS.accent, fontWeight: 800}}>Bước {active + 1}: </span>
              {PIPELINE[active].cap}
            </div>
          </div>
        </Card>
      </div>
    </Scene>
  );
};

// ---------- 4b. Đầu-cuối: video 11 phút → highlight ----------
export const EndToEndScene: React.FC<{duration: number}> = ({duration}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const stat = (value: string, label: string, i: number) => {
    const t = spring({frame: frame - 10 - i * 14, fps, config: {damping: 200}});
    return (
      <Card style={{flex: 1, textAlign: 'center', padding: '34px 20px', opacity: t, transform: `translateY(${(1 - t) * 30}px)`}}>
        <div style={{fontSize: 66, fontWeight: 800, color: i === 2 ? COLORS.accent : COLORS.text}}>{value}</div>
        <div style={{fontSize: 26, color: COLORS.dim, marginTop: 10}}>{label}</div>
      </Card>
    );
  };
  const arrow = (
    <div style={{fontSize: 60, color: COLORS.teal, alignSelf: 'center', fontWeight: 800}}>→</div>
  );
  return (
    <Scene duration={duration}>
      <Kicker>Kết quả đầu-cuối · {END2END.url}</Kicker>
      <H1 size={56}>Video {END2END.input} → còn {END2END.output} highlight</H1>
      <div style={{display: 'flex', gap: 26, marginBottom: 34}}>
        {stat(END2END.input, 'video trận đấu đầu vào', 0)}
        {arrow}
        {stat(END2END.rallies, 'pha bóng tách tự động', 1)}
        {arrow}
        {stat(END2END.output, `highlight trọn pha (${END2END.percent} thời lượng gốc)`, 2)}
      </div>
      <div style={{display: 'flex', gap: 44, alignItems: 'center'}}>
        <Card style={{flex: 1.35, padding: 18}}>
          <Img src={staticFile('steps/b6_dong_thoi_gian.png')} style={{width: '100%', borderRadius: 10}} />
        </Card>
        <div
          style={{
            flex: 1,
            borderRadius: 22,
            overflow: 'hidden',
            border: `3px solid ${COLORS.border}`,
            boxShadow: '0 24px 70px rgba(0,0,0,.5)',
          }}
        >
          <OffthreadVideo muted src={staticFile('output_preview.mp4')} style={{width: '100%', display: 'block'}} />
          <div style={{fontSize: 22, color: COLORS.dim, padding: '10px 16px', background: 'rgba(0,0,0,.35)'}}>
            Trích đoạn video highlight đầu ra (ghép các pha trọn vẹn, giữ âm thanh gốc)
          </div>
        </div>
      </div>
    </Scene>
  );
};

// ---------- 5. Demo bám bóng ----------
export const DemoScene: React.FC<{duration: number; rawFrames: number}> = ({duration, rawFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const overlayFrame = frame - rawFrames;
  const captions = DEMO_CAPTIONS.filter((c) => overlayFrame >= c.fromSec * fps);
  return (
    <Scene duration={duration}>
      <Kicker>Demo trên video thật</Kicker>
      <H1 size={56}>Vẽ quỹ đạo bóng · bóng nảy · bóng chết</H1>
      <div style={{display: 'flex', gap: 60, alignItems: 'flex-start'}}>
        <div
          style={{
            width: 440,
            borderRadius: 28,
            overflow: 'hidden',
            border: `3px solid ${COLORS.border}`,
            boxShadow: '0 30px 80px rgba(0,0,0,.5)',
          }}
        >
          {frame < rawFrames ? (
            <OffthreadVideo muted src={staticFile('demo_overlay1.mp4')} style={{width: '100%', display: 'block'}} />
          ) : (
            <OffthreadVideo muted src={staticFile('demo_overlay.mp4')} style={{width: '100%', display: 'block'}} />
          )}
        </div>
        <div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: 26, paddingTop: 10}}>
          {frame < rawFrames ? (
            <Card>
              <div style={{fontSize: 32, lineHeight: 1.45}}>
                AI bám bóng chạy trực tiếp trên hai video thật (YouTube Shorts): vòng đỏ = ứng viên bóng đang bám, đường vàng = quỹ đạo vừa vẽ.
              </div>
            </Card>
          ) : (
            captions.map((c, i) => {
              const t = spring({frame: overlayFrame - c.fromSec * fps, fps, config: {damping: 200}});
              return (
                <Card key={i} style={{opacity: t, transform: `translateX(${(1 - t) * 40}px)`}}>
                  <div style={{fontSize: 30, lineHeight: 1.4}}>{c.text}</div>
                </Card>
              );
            })
          )}
          {frame >= rawFrames ? (
            <div style={{fontSize: 24, color: COLORS.dim, marginTop: 6}}>
              Overlay sinh tự động bởi rally_evidence.track_ball — nhãn trên video: “BALL CANDIDATE — NOT VERIFIED”.
            </div>
          ) : null}
        </div>
      </div>
    </Scene>
  );
};

// ---------- 6. Thuật toán đã học ----------
export const AlgosScene: React.FC<{duration: number}> = ({duration}) => (
  <Scene duration={duration}>
    <Kicker>Kiến thức môn học</Kicker>
    <H1 size={56}>Thuật toán đã học → vị trí trong hệ thống</H1>
    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 26, marginTop: 16}}>
      <Stagger
        items={ALGOS.map((a) => a.name)}
        step={9}
        from={10}
        render={(_, i, style) => (
          <Card style={{...style, display: 'flex', alignItems: 'center', gap: 24, padding: 26}}>
            <Chip color={i % 2 ? COLORS.teal : COLORS.accent}>{ALGOS[i].name}</Chip>
            <div style={{fontSize: 27, color: COLORS.text, lineHeight: 1.35}}>{ALGOS[i].where}</div>
          </Card>
        )}
      />
    </div>
  </Scene>
);

// ---------- 7. Kết quả & trung thực ----------
export const ResultsScene: React.FC<{duration: number}> = ({duration}) => (
  <Scene duration={duration}>
    <Kicker>Kết quả</Kicker>
    <H1 size={56}>Đo được gì — và nói đúng mức bằng chứng</H1>
    <div style={{display: 'flex', gap: 30, marginBottom: 38}}>
      <Stagger
        items={RESULTS.map((r) => r.value)}
        step={10}
        from={8}
        render={(_, i, style) => (
          <Card style={{...style, flex: 1, textAlign: 'center', padding: '30px 18px'}}>
            <div style={{fontSize: 64, fontWeight: 800, color: COLORS.accent}}>{RESULTS[i].value}</div>
            <div style={{fontSize: 24, color: COLORS.dim, marginTop: 8, lineHeight: 1.35}}>{RESULTS[i].label}</div>
          </Card>
        )}
      />
    </div>
    <div style={{display: 'flex', gap: 50}}>
      <Card style={{flex: 1, padding: 20, alignSelf: 'flex-start'}}>
        <Img src={staticFile('img/do_dai_pha.png')} style={{width: '100%', borderRadius: 12}} />
        <div style={{fontSize: 23, color: COLORS.dim, marginTop: 12, textAlign: 'center'}}>
          Phân bố độ dài 154 pha trên trận thử 67 phút
        </div>
      </Card>
      <div style={{flex: 1.2, display: 'flex', flexDirection: 'column', gap: 24}}>
        <Stagger
          items={HONEST}
          step={16}
          from={30}
          render={(item, i, style) => (
            <Card style={{...style, display: 'flex', gap: 20, alignItems: 'flex-start'}}>
              <div style={{fontSize: 30, color: COLORS.accent, fontWeight: 800}}>!</div>
              <div style={{fontSize: 28, lineHeight: 1.4}}>{item}</div>
            </Card>
          )}
        />
      </div>
    </div>
  </Scene>
);

// ---------- 8. Kết ----------
export const OutroScene: React.FC<{duration: number}> = ({duration}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: frame - 6, fps, config: {damping: 200}});
  return (
    <Scene duration={duration}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', textAlign: 'center'}}>
        <div style={{opacity: pop, maxWidth: 1500}}>
          <Kicker>Cảm ơn thầy cô và các bạn</Kicker>
          <H1 size={76}>Mọi con số đều chạy lại được</H1>
          <div style={{fontSize: 34, color: COLORS.dim, lineHeight: 1.6}}>
            Code · kiểm thử · báo cáo QC · script tái lập:
            <br />
            <span style={{color: COLORS.teal, fontWeight: 700}}>{REPO}</span>
          </div>
          <div style={{fontSize: 30, color: COLORS.dim, marginTop: 40}}>
            {TEAM.map((m) => m.name).join(' · ')}
          </div>
        </div>
      </AbsoluteFill>
    </Scene>
  );
};
