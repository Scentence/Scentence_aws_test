"use client";

import React, { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html, useCursor, Sparkles, Float, Billboard } from "@react-three/drei";

interface MyPerfume {
    my_perfume_id: number;
    name: string;
    name_kr?: string;
    name_en?: string;
    brand: string;
    brand_kr?: string;
    image_url: string | null;
}

interface GlobeViewProps {
    collection?: MyPerfume[];
    isKorean?: boolean;
}

const GLOBE_RADIUS = 12;
const CARD_WIDTH = 1.6;
const CARD_HEIGHT = 2.2;
const CARD_THICKNESS = 0.05;

// [TWEAK] Hover/Focus Scale Factors
const HOVER_SCALE = 1.15;
const FOCUS_SCALE = 1.5;

const MOCK_IMAGES = [
    "https://images.unsplash.com/photo-1615634260167-c8cdede054de?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1594035910387-fea477942698?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1523293182086-7651a899d60f?auto=format&fit=crop&w=400&q=80",
];

function getPositionOnSphere(i: number, N: number, radius: number) {
    const phi = Math.acos(1 - (2 * (i + 0.5)) / N);
    const theta = Math.PI * (1 + 5 ** 0.5) * i;
    const x = radius * Math.cos(theta) * Math.sin(phi);
    const y = radius * Math.sin(theta) * Math.sin(phi);
    const z = radius * Math.cos(phi);
    return new THREE.Vector3(x, y, z);
}

// [CAMERA LOGIC]
function FocusManager({ focusedPosition, controlsRef }: { focusedPosition: THREE.Vector3 | null, controlsRef: any }) {
    const { camera } = useThree();

    useFrame((state, delta) => {
        if (!controlsRef.current) return;
        const controls = controlsRef.current;

        if (focusedPosition) {
            // [SWOOSH] 타겟으로 부드럽게 이동
            controls.target.lerp(focusedPosition, delta * 4); // Target 이동 속도

            // [ZOOM] 카메라가 타겟 앞으로 이동
            const direction = new THREE.Vector3().subVectors(camera.position, focusedPosition).normalize();
            // 타겟에서 8만큼 떨어진 지점
            const targetCamPos = focusedPosition.clone().add(direction.multiplyScalar(8));

            // Camera 이동 Speed Up (Swoosh 느낌 강화)
            camera.position.lerp(targetCamPos, delta * 4);

        } else {
            // Focus 해제 시: 단순히 Center(0,0,0)을 보게 함
            controls.target.lerp(new THREE.Vector3(0, 0, 0), delta * 2);
            // 카메라는 사용자가 둔 위치 그대로 유지 (Auto-Reset 삭제)
        }
        controls.update();
    });
    return null;
}

function PerfumeCard({
    info,
    position,
    mockImage,
    isKorean,
    focusedId,
    setFocusedId
}: {
    info: MyPerfume;
    position: THREE.Vector3;
    mockImage?: string;
    isKorean: boolean;
    focusedId: number | null;
    setFocusedId: (id: number | null) => void;
}) {
    const ref = useRef<THREE.Group>(null);
    const [hovered, setHover] = useState(false);

    // Focus Logic
    const isFocused = focusedId === info.my_perfume_id;
    const isDimmed = focusedId !== null && !isFocused;

    useCursor(hovered && !isDimmed);

    useFrame((state, delta) => {
        if (ref.current) {
            // Smooth Scale Transition
            const targetScale = isFocused ? FOCUS_SCALE : (hovered && !isDimmed ? HOVER_SCALE : 1);
            ref.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), delta * 15);
        }
    });

    const handlePointerDown = (e: any) => {
        e.stopPropagation(); // Prevent background click
        setFocusedId(isFocused ? null : info.my_perfume_id);
    };

    const displayBrand = isKorean ? (info.brand_kr || info.brand) : info.brand;
    const displayName = isKorean ? (info.name_kr || info.name) : (info.name_en || info.name);
    const displayImage = info.image_url || mockImage;

    return (
        <Float
            speed={(hovered || isFocused) ? 0 : 1} // Stop motion on hover/focus
            rotationIntensity={0}
            floatIntensity={0.5}
            floatingRange={isFocused ? [0, 0] : [-0.2, 0.2]}
        >
            <Billboard position={position} follow={true} lockX={false} lockY={false} lockZ={false}>
                <group ref={ref}>

                    {/* [HITBOX] Transparent, Large, clickable */}
                    <mesh
                        position={[0, 0, CARD_THICKNESS + 0.2]}
                        onPointerDown={handlePointerDown}
                        onPointerOver={(e) => { e.stopPropagation(); if (!isDimmed) setHover(true); }}
                        onPointerOut={() => setHover(false)}
                    >
                        <planeGeometry args={[CARD_WIDTH, CARD_HEIGHT]} />
                        <meshBasicMaterial transparent opacity={0} depthWrite={false} color="red" />
                    </mesh>

                    <AnimatedCardContent isDimmed={isDimmed} isFocused={isFocused}>

                        {/* [GOLD GLOW BACKING] 
                            MeshBasicMaterial -> Ignore Light -> Always Visible 
                            Show only on Hover/Focus 
                        */}
                        <mesh position={[0, 0, -0.06]}>
                            <boxGeometry args={[CARD_WIDTH + 0.15, CARD_HEIGHT + 0.15, 0.01]} />
                            <meshBasicMaterial
                                color="#FFD700" // Pure Gold
                                transparent
                                opacity={(hovered || isFocused) && !isDimmed ? 1 : 0}
                            />
                        </mesh>

                        {/* MAIN DARK FRAME */}
                        <mesh castShadow receiveShadow>
                            <boxGeometry args={[CARD_WIDTH, CARD_HEIGHT, CARD_THICKNESS]} />
                            <meshStandardMaterial
                                color="#1a1a1a"
                                roughness={0.7}
                                metalness={0.1}
                                transparent={true}
                                opacity={isDimmed ? 0.2 : 1}
                            />
                        </mesh>

                        {/* IMAGE PANEL */}
                        <mesh position={[0, 0.2, CARD_THICKNESS / 2 + 0.02]}>
                            <planeGeometry args={[CARD_WIDTH - 0.1, CARD_HEIGHT - 0.8]} />
                            <meshBasicMaterial
                                color="#000"
                                transparent={true}
                                opacity={isDimmed ? 0.2 : 1}
                            />
                        </mesh>

                        {/* HTML OVERLAY */}
                        {!isDimmed && (
                            <Html
                                transform
                                occlude="blending"
                                position={[0, 0, CARD_THICKNESS / 2 + 0.03]}
                                style={{
                                    width: '150px',
                                    height: '210px',
                                    pointerEvents: 'none',
                                    userSelect: 'none',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    transition: 'opacity 0.2s',
                                }}
                            >
                                <div className="w-full h-full flex flex-col p-2 font-sans antialiased text-left select-none">
                                    <div className="w-full h-[130px] bg-gray-900 rounded-sm overflow-hidden mb-3 shadow-inner relative">
                                        {displayImage && (
                                            <img
                                                src={displayImage}
                                                alt={displayName}
                                                className="w-full h-full object-cover"
                                            />
                                        )}
                                    </div>
                                    <div className="flex-1 w-full flex flex-col justify-start px-1">
                                        <span className="text-[9px] text-gray-400 font-bold uppercase tracking-widest mb-1 truncate block" style={{ color: (hovered || isFocused) ? '#FFD700' : '#9CA3AF' }}>
                                            {displayBrand}
                                        </span>
                                        <span className="text-[11px] text-white font-medium leading-snug line-clamp-2 break-keep block">
                                            {displayName}
                                        </span>
                                    </div>
                                </div>
                            </Html>
                        )}
                    </AnimatedCardContent>
                </group>
            </Billboard>
        </Float>
    );
}

function AnimatedCardContent({ isDimmed, isFocused, children }: { isDimmed: boolean, isFocused: boolean, children: React.ReactNode }) {
    const groupRef = useRef<THREE.Group>(null);
    useFrame((state, delta) => {
        if (groupRef.current) {
            // Dimmed -> Move Back (-15)
            const targetZ = isDimmed ? -15 : 0;
            groupRef.current.position.z = THREE.MathUtils.lerp(groupRef.current.position.z, targetZ, delta * 3);
        }
    });
    return <group ref={groupRef}>{children}</group>;
}

function Background({ onReset }: { onReset: () => void }) {
    return (
        <mesh onPointerDown={(e) => { e.stopPropagation(); onReset(); }} position={[0, 0, -30]} scale={[100, 100, 1]}>
            <planeGeometry />
            <meshBasicMaterial visible={false} />
        </mesh>
    );
}

export default function ArchiveGlobeView({ collection = [], isKorean = true }: GlobeViewProps) {
    const [focusedId, setFocusedId] = useState<number | null>(null);
    const controlsRef = useRef<any>(null);

    const displayConfig = useMemo(() => {
        if (collection.length > 0) return collection;
        return Array.from({ length: 30 }).map((_, i) => ({
            my_perfume_id: i,
            name: `Perfume No.${i + 1}`,
            name_en: `Perfume No.${i + 1}`,
            name_kr: `센텐스 컬렉션 ${i + 1}`,
            brand: "SCENTENCE",
            brand_kr: "센텐스",
            image_url: null,
        }));
    }, [collection]);

    // Focus Position Logic
    const focusedPosition = useMemo(() => {
        if (focusedId === null) return null;
        const idx = displayConfig.findIndex(item => item.my_perfume_id === focusedId);
        if (idx === -1) return null;
        return getPositionOnSphere(idx, displayConfig.length, GLOBE_RADIUS);
    }, [focusedId, displayConfig]);

    return (
        <div className="w-full h-[700px] rounded-[2rem] overflow-hidden border border-gray-900 shadow-2xl relative bg-black select-none">

            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900/30 via-black to-black pointer-events-none" />

            {/* Camera Setup: Far Clip 1000 for visibility */}
            <Canvas shadows camera={{ position: [0, 0, 38], fov: 38, near: 0.1, far: 1000 }} dpr={[1, 2]}>

                {/* Visuals: Sparkles */}
                <Sparkles count={3000} scale={120} size={4} speed={0.4} opacity={0.5} color="#88ccff" />
                <Sparkles count={500} scale={80} size={6} speed={0.6} opacity={0.8} color="#ffd700" noise={1} />

                <ambientLight intensity={0.6} />
                <spotLight position={[10, 10, 20]} angle={0.5} penumbra={1} intensity={1} color="#ffffff" />

                <Background onReset={() => setFocusedId(null)} />
                <FocusManager focusedPosition={focusedPosition} controlsRef={controlsRef} />

                <group>
                    {displayConfig.map((item, idx) => {
                        const position = getPositionOnSphere(idx, displayConfig.length, GLOBE_RADIUS);
                        const mockImg = MOCK_IMAGES[idx % MOCK_IMAGES.length];

                        return (
                            <PerfumeCard
                                key={item.my_perfume_id}
                                info={item}
                                position={position}
                                mockImage={mockImg}
                                isKorean={isKorean}
                                focusedId={focusedId}
                                setFocusedId={setFocusedId}
                            />
                        );
                    })}
                </group>

                <OrbitControls
                    ref={controlsRef}
                    enableRotate={true}
                    enablePan={false}
                    enableZoom={true} // Enabled
                    minDistance={2} // Allow close zoom
                    maxDistance={100} // Allow far zoom (no sticking)
                    autoRotate={!focusedId}
                    autoRotateSpeed={0.05}
                    dampingFactor={0.05}
                />
            </Canvas>

            <div className="absolute bottom-6 left-0 w-full text-center pointer-events-none opacity-30 select-none">
                <span className="text-[10px] text-white tracking-[0.2em] font-light font-sans">
                    CLICK TO FOCUS • SCROLL TO ZOOM
                </span>
            </div>
        </div>
    );
}