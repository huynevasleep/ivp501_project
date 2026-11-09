import React from 'react';
import {Sequence} from 'remotion';
import {AlgosScene, DemoScene, GoalsScene, OutroScene, PipelineScene, ResultsScene, TeamScene, TitleScene} from './scenes';

// Thời lượng từng cảnh tính theo khung hình (30 fps).
const FPS = 30;
export const SCENES = {
  title: 5 * FPS,
  team: 9 * FPS,
  goals: 10 * FPS,
  pipeline: 30 * FPS,
  demoRaw: 4 * FPS,          // phần video gốc trong cảnh demo
  demoOverlay: Math.round(10.5 * FPS),
  algos: 13 * FPS,
  results: 18 * FPS,
  outro: 9 * FPS,
};
const demo = SCENES.demoRaw + SCENES.demoOverlay;
export const TOTAL =
  SCENES.title + SCENES.team + SCENES.goals + SCENES.pipeline + demo + SCENES.algos + SCENES.results + SCENES.outro;

export const Main: React.FC = () => {
  let at = 0;
  const next = (d: number) => {
    const from = at;
    at += d;
    return from;
  };
  return (
    <>
      <Sequence from={next(SCENES.title)} durationInFrames={SCENES.title}>
        <TitleScene duration={SCENES.title} />
      </Sequence>
      <Sequence from={next(SCENES.team)} durationInFrames={SCENES.team}>
        <TeamScene duration={SCENES.team} />
      </Sequence>
      <Sequence from={next(SCENES.goals)} durationInFrames={SCENES.goals}>
        <GoalsScene duration={SCENES.goals} />
      </Sequence>
      <Sequence from={next(SCENES.pipeline)} durationInFrames={SCENES.pipeline}>
        <PipelineScene duration={SCENES.pipeline} />
      </Sequence>
      <Sequence from={next(demo)} durationInFrames={demo}>
        <DemoScene duration={demo} rawFrames={SCENES.demoRaw} />
      </Sequence>
      <Sequence from={next(SCENES.algos)} durationInFrames={SCENES.algos}>
        <AlgosScene duration={SCENES.algos} />
      </Sequence>
      <Sequence from={next(SCENES.results)} durationInFrames={SCENES.results}>
        <ResultsScene duration={SCENES.results} />
      </Sequence>
      <Sequence from={next(SCENES.outro)} durationInFrames={SCENES.outro}>
        <OutroScene duration={SCENES.outro} />
      </Sequence>
    </>
  );
};
