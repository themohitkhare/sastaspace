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

const BOARD_PRESETS = [
    { value: 'CLASSIC', label: 'CLASSIC' },
    { value: 'UGC_24', label: 'UGC 24' },
]

const CASH_MULTIPLIERS = [
    { value: 0.5, label: '0.5x' },
    { value: 1.0, label: '1x' },
    { value: 2.0, label: '2x' },
]

const TAX_RATES = [
    { value: 0.05, label: '5%' },
    { value: 0.10, label: '10%' },
    { value: 0.15, label: '15%' },
]

export default function GameSettingsPanel({ settings, onUpdate, onSave, hasChanges, isHost, alwaysExpanded = false }) {
    const [expanded, setExpanded] = useState(false)
    const showContent = alwaysExpanded || expanded

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
        onUpdate(key, value)
    }

    return (
        <div className={`bg-zinc-800 border transition-colors ${hasChanges ? 'border-yellow-500' : 'border-zinc-700'}`}>
            {!alwaysExpanded ? (
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
            ) : (
                <div className="p-3 bg-zinc-800/50 flex items-center justify-between border-b border-zinc-700">
                    <span className="font-data font-bold text-sm text-zinc-200 flex items-center gap-2">
                        ⚙️ GAME SETTINGS {hasChanges && <span className="text-yellow-500 text-xs ml-2">● UNSAVED</span>}
                    </span>
                </div>
            )}

            {showContent && (
                <div className="p-3 border-t border-zinc-700 space-y-4">
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

                    <div className="pt-2 border-t border-zinc-700">
                        <div className="text-xs font-data text-zinc-500 text-center">
                            {settings?.win_condition === 'FIRST_TO_CASH' && `First to $${settings?.target_cash || 10000} wins`}
                        </div>
                    </div>

                    {/* BOARD section */}
                    <div className="mt-4 pt-4 border-t-2 border-black">
                        <div className="text-xs font-zero mb-2 opacity-60">BOARD</div>
                        <div className="flex gap-1 flex-wrap">
                            {BOARD_PRESETS.map((preset) => (
                                <button
                                    key={preset.value}
                                    onClick={() => onUpdate('board_preset', preset.value)}
                                    className={`px-3 py-1 text-xs font-zero border-2 border-black transition-all ${
                                        settings?.board_preset === preset.value
                                            ? 'bg-black text-white shadow-brutal-sm'
                                            : 'bg-white hover:bg-gray-100'
                                    }`}
                                >
                                    {preset.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* ECONOMY section */}
                    <div className="mt-4 pt-4 border-t-2 border-black">
                        <div className="text-xs font-zero mb-2 opacity-60">ECONOMY</div>

                        <div className="mb-2">
                            <div className="text-[10px] font-zero opacity-50 mb-1">STARTING CASH</div>
                            <div className="flex gap-1">
                                {CASH_MULTIPLIERS.map((mult) => (
                                    <button
                                        key={mult.value}
                                        onClick={() => onUpdate('starting_cash_multiplier', mult.value)}
                                        className={`px-3 py-1 text-xs font-zero border-2 border-black transition-all ${
                                            settings?.starting_cash_multiplier === mult.value
                                                ? 'bg-black text-white shadow-brutal-sm'
                                                : 'bg-white hover:bg-gray-100'
                                        }`}
                                    >
                                        {mult.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <div className="text-[10px] font-zero opacity-50 mb-1">TAX RATE</div>
                            <div className="flex gap-1">
                                {TAX_RATES.map((rate) => (
                                    <button
                                        key={rate.value}
                                        onClick={() => onUpdate('income_tax_rate', rate.value)}
                                        className={`px-3 py-1 text-xs font-zero border-2 border-black transition-all ${
                                            settings?.income_tax_rate === rate.value
                                                ? 'bg-black text-white shadow-brutal-sm'
                                                : 'bg-white hover:bg-gray-100'
                                        }`}
                                    >
                                        {rate.label}
                                    </button>
                                ))}
                            </div>
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
