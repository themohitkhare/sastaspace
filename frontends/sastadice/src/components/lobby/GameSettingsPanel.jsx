import { useState } from 'react'

const WIN_CONDITIONS = [
    { value: 'SUDDEN_DEATH', label: 'Sudden Death', desc: 'Richest at round limit wins' },
    { value: 'LAST_STANDING', label: 'Last Standing', desc: 'Play until 1 player remains' },
    { value: 'FIRST_TO_CASH', label: 'First to Cash', desc: 'Race to target cash amount' },
]

const CHAOS_LEVELS = [
    { value: 'CHILL', label: 'Chill', desc: 'Fewer events, stable' },
    { value: 'NORMAL', label: 'Normal', desc: 'Balanced chaos' },
    { value: 'CHAOS', label: 'Chaos', desc: 'Maximum variance' },
]

const ROUND_PRESETS = [
    { value: 15, label: 'Quick (15)' },
    { value: 30, label: 'Standard (30)' },
    { value: 50, label: 'Long (50)' },
    { value: 0, label: '∞ Unlimited' },
]

export default function GameSettingsPanel({ settings, onUpdate, onSave, hasChanges, isHost }) {
    const [expanded, setExpanded] = useState(false)

    if (!isHost) {
        // ... existing read-only view ...
        return (
            <div className="bg-zinc-800 p-3 border border-zinc-700">
                <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-data text-zinc-400">GAME MODE</span>
                </div>
                <div className="flex flex-wrap gap-2">
                    <span className="px-2 py-1 bg-sasta-accent/20 text-sasta-accent text-xs font-data">
                        {settings?.win_condition || 'SUDDEN_DEATH'}
                    </span>
                    <span className="px-2 py-1 bg-zinc-700 text-zinc-300 text-xs font-data">
                        {settings?.round_limit ? `${settings.round_limit} ROUNDS` : '∞ ROUNDS'}
                    </span>
                </div>
            </div>
        )
    }

    const handleChange = (key, value) => {
        onUpdate({ ...settings, [key]: value })
    }

    return (
        <div className={`bg-zinc-800 border transition-colors ${hasChanges ? 'border-yellow-500' : 'border-zinc-700'}`}>
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full p-3 flex justify-between items-center hover:bg-zinc-700/50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <span className="text-lg">⚙️</span>
                    <span className="font-data font-bold text-sm text-zinc-200">
                        GAME SETTINGS {hasChanges && <span className="text-yellow-500 text-xs ml-2">● UNSAVED</span>}
                    </span>
                </div>
                <span className="text-zinc-400 text-lg">{expanded ? '▲' : '▼'}</span>
            </button>

            {expanded && (
                <div className="p-3 border-t border-zinc-700 space-y-4">
                    {/* Win Condition */}
                    <div>
                        <label className="block text-xs font-data text-zinc-400 mb-2">WIN CONDITION</label>
                        <div className="grid grid-cols-3 gap-1">
                            {WIN_CONDITIONS.map((wc) => (
                                <button
                                    key={wc.value}
                                    onClick={() => handleChange('win_condition', wc.value)}
                                    className={`p-2 text-xs font-data text-center transition-colors ${settings?.win_condition === wc.value
                                        ? 'bg-sasta-accent text-sasta-black font-bold'
                                        : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
                                        }`}
                                >
                                    {wc.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Round Limit */}
                    {settings?.win_condition !== 'LAST_STANDING' && (
                        <div>
                            <label className="block text-xs font-data text-zinc-400 mb-2">ROUND LIMIT</label>
                            <div className="grid grid-cols-4 gap-1">
                                {ROUND_PRESETS.map((rp) => (
                                    <button
                                        key={rp.value}
                                        onClick={() => handleChange('round_limit', rp.value)}
                                        className={`p-2 text-xs font-data text-center transition-colors ${settings?.round_limit === rp.value
                                            ? 'bg-sasta-accent text-sasta-black font-bold'
                                            : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
                                            }`}
                                    >
                                        {rp.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Chaos Level */}
                    <div>
                        <label className="block text-xs font-data text-zinc-400 mb-2">CHAOS LEVEL</label>
                        <div className="grid grid-cols-3 gap-1">
                            {CHAOS_LEVELS.map((cl) => (
                                <button
                                    key={cl.value}
                                    onClick={() => handleChange('chaos_level', cl.value)}
                                    className={`p-2 text-xs font-data text-center transition-colors ${settings?.chaos_level === cl.value
                                        ? 'bg-sasta-accent text-sasta-black font-bold'
                                        : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
                                        }`}
                                >
                                    {cl.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Feature Toggles */}
                    <div>
                        <label className="block text-xs font-data text-zinc-400 mb-2">FEATURES</label>
                        <div className="grid grid-cols-2 gap-2">
                            <ToggleButton
                                label="Doubles Bonus"
                                value={settings?.doubles_give_extra_turn !== false}
                                onChange={(v) => handleChange('doubles_give_extra_turn', v)}
                            />
                            <ToggleButton
                                label="Stimulus Check"
                                value={settings?.enable_stimulus !== false}
                                onChange={(v) => handleChange('enable_stimulus', v)}
                            />
                            <ToggleButton
                                label="Black Market"
                                value={settings?.enable_black_market !== false}
                                onChange={(v) => handleChange('enable_black_market', v)}
                            />
                            <ToggleButton
                                label="Auctions"
                                value={settings?.enable_auctions !== false}
                                onChange={(v) => handleChange('enable_auctions', v)}
                            />
                        </div>
                    </div>

                    {/* Summary */}
                    <div className="pt-2 border-t border-zinc-700">
                        <div className="text-xs font-data text-zinc-500 text-center">
                            {settings?.win_condition === 'FIRST_TO_CASH' && `First to $${settings?.target_cash || 10000} wins`}
                        </div>
                    </div>

                    {hasChanges && (
                        <button
                            onClick={onSave}
                            className="w-full py-2 bg-sasta-accent text-sasta-black font-bold font-data text-sm hover:bg-white transition-colors animate-pulse"
                        >
                            SAVE CHANGES
                        </button>
                    )}
                </div>
            )}
        </div>
    )
}

function ToggleButton({ label, value, onChange }) {
    return (
        <button
            onClick={() => onChange(!value)}
            className={`p-2 text-xs font-data flex items-center justify-between transition-colors ${value
                ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                : 'bg-zinc-700/50 text-zinc-500 border border-zinc-600'
                }`}
        >
            <span>{label}</span>
            <span>{value ? '✓' : '✗'}</span>
        </button>
    )
}
