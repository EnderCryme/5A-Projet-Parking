library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity barrier_motor_top is
  port (
    clk         : in  STD_LOGIC;                       -- E3 : 100 MHz
    reset       : in  STD_LOGIC;                       -- BTNC (actif haut)
    enable      : in  STD_LOGIC;                       -- SW0
    direction   : in  STD_LOGIC;                       -- SW1
    speed_sel   : in  STD_LOGIC_VECTOR(1 downto 0);    -- SW3,SW2
    prox_sensor : in  STD_LOGIC;                       -- JB1 (1 = présence)
    led_sensor  : out STD_LOGIC;                       -- témoin présence
    led_dir     : out STD_LOGIC;                       -- témoin direction
    buzzer_out  : out STD_LOGIC;                       -- JD10 -> buzzer +
    phases      : out STD_LOGIC_VECTOR(3 downto 0)     -- JA1..JA4 -> ULN2003 IN1..IN4
  );
end barrier_motor_top;

architecture Structural of barrier_motor_top is
  --------------------------------------------------------------------
  -- Composants
  --------------------------------------------------------------------
  component step_clock_sel is
    port (
      clk       : in  STD_LOGIC;
      reset     : in  STD_LOGIC;
      enable    : in  STD_LOGIC;
      speed_sel : in  STD_LOGIC_VECTOR(1 downto 0);
      step_ce   : out STD_LOGIC
    );
  end component;

  component fsm_hightorque is
    port (
      clk       : in  STD_LOGIC;
      reset     : in  STD_LOGIC;
      step_ce   : in  STD_LOGIC;
      enable    : in  STD_LOGIC;
      direction : in  STD_LOGIC;
      phases    : out STD_LOGIC_VECTOR(3 downto 0)
    );
  end component;

  --------------------------------------------------------------------
  -- Signaux internes
  --------------------------------------------------------------------
  signal step_ce_s     : STD_LOGIC;
  signal motor_enable  : STD_LOGIC;

  -- Capteur (d'après ton retour: 1 = présence)
  signal prox_active   : STD_LOGIC;

  -- Direction : synchro 2 FF + possibilité d'inverser facilement
  signal dir_s1, dir_s2 : STD_LOGIC := '0';
  signal dir_eff        : STD_LOGIC;
  constant INVERT_DIR   : STD_LOGIC := '0';  -- passe à '1' si le sens est inversé

  -- Buzzer (~2 kHz quand moteur actif)
  -- f = clk/(2*N) -> pour 2 kHz : N = 100e6 / (2*2000) = 25_000
  constant BUZ_TOGGLE_N : integer := 25000 - 1;
  signal buz_cnt  : integer := 0;
  signal buz_tone : STD_LOGIC := '0';

begin
  --------------------------------------------------------------------
  -- Capteur + LED
  --------------------------------------------------------------------
  prox_active <= prox_sensor;   -- 1 = présence détectée
  led_sensor  <= prox_active;

  -- Le moteur ne tourne QUE si SW0=1 ET présence détectée
  motor_enable <= enable and prox_active;

  --------------------------------------------------------------------
  -- Direction : synchronisation + inversion optionnelle
  --------------------------------------------------------------------
  process(clk)
  begin
    if rising_edge(clk) then
      dir_s1 <= direction;
      dir_s2 <= dir_s1;
    end if;
  end process;

  dir_eff  <= dir_s2 xor INVERT_DIR;
  led_dir  <= dir_eff;  -- LED direction = 1 quand on demande l'autre sens

  --------------------------------------------------------------------
  -- Buzzer : carré ~2 kHz quand le moteur est actif
  --------------------------------------------------------------------
  process(clk)
  begin
    if rising_edge(clk) then
      if reset = '1' or motor_enable = '0' then
        buz_cnt  <= 0;
        buz_tone <= '0';
      else
        if buz_cnt = BUZ_TOGGLE_N then
          buz_cnt  <= 0;
          buz_tone <= not buz_tone;
        else
          buz_cnt <= buz_cnt + 1;
        end if;
      end if;
    end if;
  end process;

  buzzer_out <= buz_tone;

  --------------------------------------------------------------------
  -- Générateur de ticks (vitesse) + FSM moteur
  --------------------------------------------------------------------
  u_clk : step_clock_sel
    port map (
      clk       => clk,
      reset     => reset,
      enable    => motor_enable,
      speed_sel => speed_sel,
      step_ce   => step_ce_s
    );

  u_fsm : fsm_hightorque
    port map (
      clk       => clk,
      reset     => reset,
      step_ce   => step_ce_s,
      enable    => motor_enable,
      direction => dir_eff,      -- on applique la direction synchronisée
      phases    => phases
    );

end Structural;
